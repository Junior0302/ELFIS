"""Context Builder — assemble un contexte borné pour le LLM (optimisation coûts)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai_assistant.memory import ConversationMemory
from app.ai_assistant.tools import AssistantTools, detect_intent
from app.financial.alerts import build_alerts
from app.financial.engine import FinancialEngine
from app.financial.health import compute_health_score
from app.models_saas import Organization

MAX_KPI_ITEMS = 9
MAX_ALERTS = 5
MAX_ACTIVITY = 5
MAX_HISTORY_TURNS = 4
MAX_CONTEXT_CHARS = 6000


class ContextBuilder:
    """Construit automatiquement le contexte à partir des moteurs internes."""

    def __init__(self, db: Session, organization_id: int, user_id: int | None = None):
        self.db = db
        self.organization_id = organization_id
        self.user_id = user_id
        self.financial = FinancialEngine(db, publish_events=False)
        self.tools = AssistantTools(db, organization_id)
        self.memory = ConversationMemory(db, organization_id, user_id)

    def build(self, question: str) -> dict[str, Any]:
        intent = detect_intent(question)
        snap = self.financial.snapshot(self.organization_id)
        kpis = self.financial.kpis(self.organization_id)
        alerts = build_alerts(snap)
        health = compute_health_score(snap)
        activity = self.financial.recent_activity(self.organization_id, limit=MAX_ACTIVITY)

        org = self.db.query(Organization).filter(Organization.id == self.organization_id).first()
        overview = {
            "kpis": [
                {
                    "id": k.id,
                    "label": k.label,
                    "value": k.value,
                    "status": k.status.value,
                    "hint": k.hint,
                }
                for k in kpis[:MAX_KPI_ITEMS]
            ],
            "alerts": [
                {"code": a.code, "severity": a.severity.value, "title": a.title}
                for a in alerts[:MAX_ALERTS]
            ],
            "health": {
                "score": health.get("score"),
                "grade": health.get("grade"),
                "state": health.get("state"),
            },
            "sync": snap["sync"],
            "documents_to_process": snap["documents_to_process"],
            "has_data": snap["has_data"],
            "recent_activity": activity,
            "computed_at": snap["computed_at"],
        }

        context = {
            "intent": intent,
            "organization": {"id": self.organization_id, "name": org.name if org else ""},
            "data_as_of": snap["computed_at"],
            "overview": overview,
            "preferences": self.memory.get_preferences(),
            "history": self.memory.recent_turns(limit=MAX_HISTORY_TURNS),
            "tool_names": self.tools.names(),
            "built_at": datetime.utcnow().isoformat(),
        }
        serialized = json.dumps(context, default=str, ensure_ascii=False)
        if len(serialized) > MAX_CONTEXT_CHARS:
            context["history"] = context["history"][-2:]
            context["overview"]["recent_activity"] = activity[:2]
            context["truncated"] = True
        return context

    def compact_for_llm(self, context: dict[str, Any], tool_results: list[dict]) -> str:
        payload = {
            "organization": context.get("organization"),
            "data_as_of": context.get("data_as_of"),
            "intent": context.get("intent"),
            "preferences": context.get("preferences"),
            "tool_results": tool_results,
            "rules": [
                "N'invente jamais de chiffre absent des tool_results.",
                "Sépare clairement faits, estimations, recommandations et manques.",
                "Si une donnée manque, dis-le dans missing.",
            ],
        }
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) > MAX_CONTEXT_CHARS:
            text = text[:MAX_CONTEXT_CHARS] + "…"
        return text
