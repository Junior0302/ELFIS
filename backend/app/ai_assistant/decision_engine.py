"""Decision Engine — unique orchestrateur de l'AI Financial Assistant.

Le chat ne dialogue jamais directement avec les moteurs.
Flux : intent → outils → contexte → (LLM optionnel) → validation → formatage.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.ai.providers.openai_provider import OpenAIProvider
from app.ai_assistant.context_builder import ContextBuilder
from app.ai_assistant.events import publish_chat_completed
from app.ai_assistant.memory import ConversationMemory
from app.ai_assistant.observability import cost_from_tokens, persist_run, response_cache
from app.ai_assistant.response_formatter import format_deterministic, merge_llm_enrichment
from app.ai_assistant.tools import INTENT_TOOLS, AssistantTools, detect_intent
from app.ai_assistant.types import AssistantRunMetrics, StructuredAnswer, ToolResult
from app.config import settings

SYSTEM_PROMPT = (
    "Tu es l'AI Financial Assistant d'ELFIS Core. "
    "Tu expliques, résumes et conseilles UNIQUEMENT à partir des tool_results JSON fournis. "
    "Tu n'inventes JAMAIS de chiffre, client, date ou opération. "
    "Réponds en JSON avec les clés : summary (string), recommendations "
    "(array d'objets {text, why}). "
    "Si une donnée manque, ne la comble pas."
)


class DecisionEngine:
    """Moteur central — seul point d'entrée conversationnel."""

    def __init__(
        self,
        db: Session,
        *,
        use_llm: bool | None = None,
        use_cache: bool = True,
    ):
        self.db = db
        self.use_llm = (
            bool(settings.openai_api_key) if use_llm is None else use_llm
        )
        self.use_cache = use_cache

    def chat(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        question: str,
        stream: bool = False,
    ) -> dict[str, Any]:
        if stream:
            # Le streaming est exposé via stream_chat() ; ici on retourne le résultat final.
            chunks = list(self.stream_chat(organization_id=organization_id, user_id=user_id, question=question))
            final = next((c for c in reversed(chunks) if c.get("type") == "final"), None)
            return final["payload"] if final else {"ok": False, "error": "stream vide"}

        started = time.monotonic()
        metrics = AssistantRunMetrics()
        question = (question or "").strip()
        if len(question) < 3:
            return {"ok": False, "error": "Question trop courte"}

        builder = ContextBuilder(self.db, organization_id, user_id)
        context = builder.build(question)
        intent = context["intent"]

        # Cache intelligent (réponse déterministe + fingerprint données)
        fingerprint = hashlib.sha256(
            json.dumps(context.get("overview"), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        cache_key = response_cache.key(organization_id, question, fingerprint)
        if self.use_cache:
            cached = response_cache.get(cache_key)
            if cached is not None:
                metrics.cache_hit = True
                metrics.latency_ms = (time.monotonic() - started) * 1000
                metrics.tools_called = list(cached.get("tools_used") or [])
                run = persist_run(
                    self.db,
                    organization_id=organization_id,
                    user_id=user_id,
                    question=question,
                    metrics=metrics,
                )
                return {**cached, "run_id": run.id, "cache_hit": True}

        tools = AssistantTools(self.db, organization_id)
        tool_names = INTENT_TOOLS.get(intent, INTENT_TOOLS["overview"])
        # Recherche : passer le texte question comme q
        results: list[ToolResult] = []
        for name in tool_names:
            kwargs: dict[str, Any] = {}
            if name == "search_transactions":
                kwargs["q"] = question
                kwargs["limit"] = 10
            results.append(tools.call(name, **kwargs))
        metrics.tools_called = [r.tool for r in results if r.ok]

        answer = format_deterministic(intent, results, question=question)

        llm_meta: dict[str, Any] = {}
        if self.use_llm and intent != "help" and results:
            answer, llm_meta = self._enrich_with_llm(builder, context, results, answer)
            metrics.llm_called = bool(llm_meta.get("called"))
            metrics.llm_latency_ms = float(llm_meta.get("latency_ms") or 0)
            metrics.input_tokens = llm_meta.get("input_tokens")
            metrics.output_tokens = llm_meta.get("output_tokens")
            metrics.estimated_cost = llm_meta.get("estimated_cost")

        metrics.latency_ms = (time.monotonic() - started) * 1000
        run = persist_run(
            self.db,
            organization_id=organization_id,
            user_id=user_id,
            question=question,
            metrics=metrics,
        )

        memory = ConversationMemory(self.db, organization_id, user_id)
        message, conversation_id = memory.persist_turn(
            question=question, answer=answer, run_id=run.id
        )
        if message is not None:
            try:
                publish_chat_completed(
                    self.db,
                    organization_id=organization_id,
                    message_id=message.id,
                    tools_used=list(answer.tools_used),
                    confidence=answer.confidence.value,
                    latency_ms=metrics.latency_ms,
                )
            except Exception:
                pass

        payload = self._to_payload(answer, conversation_id, message.id if message else None, run.id, metrics)
        if self.use_cache and not metrics.error:
            response_cache.set(cache_key, {k: v for k, v in payload.items() if k != "run_id"})
        return payload

    def stream_chat(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        question: str,
    ) -> Iterator[dict[str, Any]]:
        """Streaming SSE-friendly : statut → sections → final."""
        yield {"type": "status", "message": "Analyse de la question…"}
        intent = detect_intent(question)
        yield {"type": "status", "message": f"Intention détectée : {intent}"}
        yield {"type": "status", "message": "Appel des outils internes…"}

        result = self.chat(organization_id=organization_id, user_id=user_id, question=question, stream=False)
        structured = result.get("structured") or {}
        if structured.get("facts"):
            yield {"type": "section", "name": "facts", "items": structured["facts"]}
        if structured.get("estimates"):
            yield {"type": "section", "name": "estimates", "items": structured["estimates"]}
        if structured.get("recommendations"):
            yield {"type": "section", "name": "recommendations", "items": structured["recommendations"]}
        if structured.get("missing"):
            yield {"type": "section", "name": "missing", "items": structured["missing"]}
        yield {"type": "final", "payload": result}

    def get_context(self, organization_id: int, user_id: int | None = None, question: str = "vue d'ensemble") -> dict:
        return ContextBuilder(self.db, organization_id, user_id).build(question)

    def list_tools(self, organization_id: int) -> list[dict]:
        return [s.model_dump() for s in AssistantTools(self.db, organization_id).specs()]

    def _enrich_with_llm(
        self,
        builder: ContextBuilder,
        context: dict,
        results: list[ToolResult],
        base: StructuredAnswer,
    ) -> tuple[StructuredAnswer, dict[str, Any]]:
        meta: dict[str, Any] = {"called": False}
        try:
            provider = OpenAIProvider()
            model = settings.openai_chat_model
            user_payload = builder.compact_for_llm(
                context, [r.model_dump(mode="json") for r in results if r.ok]
            )
            started = time.monotonic()
            response = provider.execute_structured(
                model=model,
                system=SYSTEM_PROMPT,
                user=user_payload,
                temperature=0.2,
            )
            meta = {
                "called": True,
                "latency_ms": (time.monotonic() - started) * 1000,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost": cost_from_tokens(
                    "openai", model, response.input_tokens, response.output_tokens
                ),
            }
            enriched = merge_llm_enrichment(base, response.structured_output)
            return enriched, meta
        except Exception as exc:  # noqa: BLE001
            meta["error"] = str(exc)[:200]
            return base, meta

    @staticmethod
    def _to_payload(
        answer: StructuredAnswer,
        conversation_id: int | None,
        message_id: str | None,
        run_id: str,
        metrics: AssistantRunMetrics,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "agent": "AI Financial Assistant",
            "answer": answer.to_plain_text(),
            "structured": answer.model_dump(mode="json"),
            "conversation_id": conversation_id,
            "message_id": message_id,
            "run_id": run_id,
            "confidence": answer.confidence.value,
            "sources": answer.sources,
            "tools_used": answer.tools_used,
            "actions": [a.model_dump() for a in answer.actions],
            "metrics": metrics.model_dump(),
            "cache_hit": metrics.cache_hit,
        }
