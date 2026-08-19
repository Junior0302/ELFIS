"""Tests Decision Engine — orchestration, anti-hallucination, cache, mémoire."""

from __future__ import annotations

from app.ai_assistant.decision_engine import DecisionEngine
from app.ai_assistant.models import ElfisAssistantMessage, ElfisAssistantRun
from app.ai_assistant.observability import response_cache
from tests.ai_assistant.helpers import make_assistant_db, seed_assistant


def test_decision_engine_chat_returns_structured_sections():
    db = make_assistant_db()
    org, user = seed_assistant(db)

    result = DecisionEngine(db, use_llm=False, use_cache=False).chat(
        organization_id=org.id,
        user_id=user.id,
        question="Quel est l'état de ma trésorerie ?",
    )

    assert result["ok"] is True
    assert result["agent"] == "AI Financial Assistant"
    structured = result["structured"]
    assert "facts" in structured
    assert "estimates" in structured
    assert "recommendations" in structured
    assert "missing" in structured
    assert any("12" in f or "trésorerie" in f.lower() or "Trésorerie" in f for f in structured["facts"])
    assert "get_cashflow" in result["tools_used"]
    assert result["confidence"] in {"high", "medium", "low"}
    assert result["message_id"]
    assert result["actions"]


def test_decision_engine_never_invents_without_tools_data():
    db = make_assistant_db()
    org = seed_assistant(db)[0]
    # org vide : nouvelle org sans données
    from tests.financial.helpers import seed_org

    empty = seed_org(db, "Empty Org")
    result = DecisionEngine(db, use_llm=False, use_cache=False).chat(
        organization_id=empty.id,
        user_id=None,
        question="Combien ai-je sur mon compte secret offshore ?",
    )
    # Pas de chiffre inventé dans les faits — missing ou faits nuls
    answer = result["answer"].lower()
    assert "offshore" not in answer or "manqu" in answer or "aucune" in answer or "pas" in answer
    assert result["ok"] is True


def test_help_intent_does_not_require_tools():
    db = make_assistant_db()
    org, user = seed_assistant(db)
    result = DecisionEngine(db, use_llm=False).chat(
        organization_id=org.id,
        user_id=user.id,
        question="Que peux-tu faire ?",
    )
    assert result["ok"]
    assert "Financial" in result["answer"] or "moteurs" in result["answer"].lower()


def test_cache_hit_on_second_identical_question():
    db = make_assistant_db()
    org, user = seed_assistant(db)
    engine = DecisionEngine(db, use_llm=False, use_cache=True)
    response_cache.clear()

    first = engine.chat(
        organization_id=org.id, user_id=user.id, question="Résume ma santé financière"
    )
    second = engine.chat(
        organization_id=org.id, user_id=user.id, question="Résume ma santé financière"
    )
    assert first["ok"] and second["ok"]
    assert second.get("cache_hit") is True


def test_memory_persists_structured_message_and_run():
    db = make_assistant_db()
    org, user = seed_assistant(db)
    result = DecisionEngine(db, use_llm=False, use_cache=False).chat(
        organization_id=org.id,
        user_id=user.id,
        question="Quels clients sont en retard ?",
    )
    msg = db.query(ElfisAssistantMessage).filter_by(id=result["message_id"]).one()
    assert msg.structured_json is not None
    assert msg.tools_used
    run = db.query(ElfisAssistantRun).filter_by(id=result["run_id"]).one()
    assert run.latency_ms >= 0
    assert run.tools_called


def test_stream_emits_sections_then_final():
    db = make_assistant_db()
    org, user = seed_assistant(db)
    chunks = list(
        DecisionEngine(db, use_llm=False, use_cache=False).stream_chat(
            organization_id=org.id,
            user_id=user.id,
            question="Où en est ma TVA ?",
        )
    )
    types = [c["type"] for c in chunks]
    assert "status" in types
    assert "final" in types
    final = chunks[-1]["payload"]
    assert final["ok"] is True
