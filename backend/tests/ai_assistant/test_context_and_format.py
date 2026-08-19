"""Tests Context Builder + formatage (séparation faits/estimations/recommandations)."""

from __future__ import annotations

from app.ai_assistant.context_builder import ContextBuilder, MAX_CONTEXT_CHARS
from app.ai_assistant.response_formatter import format_deterministic, merge_llm_enrichment
from app.ai_assistant.tools import AssistantTools
from app.ai_assistant.types import ConfidenceLevel, StructuredAnswer
from tests.ai_assistant.helpers import make_assistant_db, seed_assistant


def test_context_builder_assembles_bounded_context():
    db = make_assistant_db()
    org, user = seed_assistant(db)
    ctx = ContextBuilder(db, org.id, user.id).build("Quel est mon health score ?")

    assert ctx["intent"] == "health"
    assert ctx["organization"]["id"] == org.id
    assert len(ctx["overview"]["kpis"]) == 9
    assert "sync" in ctx["overview"]
    assert "tool_names" in ctx
    assert len(str(ctx)) < MAX_CONTEXT_CHARS * 3


def test_structured_answer_has_four_sections():
    db = make_assistant_db()
    org, _ = seed_assistant(db)
    tools = AssistantTools(db, org.id)
    results = [
        tools.call("get_cashflow"),
        tools.call("get_unpaid_invoices"),
        tools.call("get_alerts"),
    ]
    answer = format_deterministic("cashflow", results)

    assert isinstance(answer, StructuredAnswer)
    assert answer.facts
    assert isinstance(answer.estimates, list)
    assert isinstance(answer.recommendations, list)
    assert isinstance(answer.missing, list)
    assert answer.tools_used
    assert answer.confidence in ConfidenceLevel
    plain = answer.to_plain_text()
    assert "Faits vérifiés" in plain


def test_recommendations_are_explainable():
    db = make_assistant_db()
    org, _ = seed_assistant(db)
    tools = AssistantTools(db, org.id)
    answer = format_deterministic(
        "unpaid", [tools.call("get_unpaid_invoices"), tools.call("get_alerts")]
    )
    assert answer.recommendations
    for rec in answer.recommendations:
        assert rec.explanation.why
        assert rec.explanation.data_used
        assert rec.explanation.calculation
        assert rec.explanation.confidence in ConfidenceLevel


def test_llm_cannot_inject_invented_amounts_in_summary():
    base = StructuredAnswer(
        summary="Trésorerie à 12 000 €.",
        facts=["Trésorerie actuelle : 12 000,00 €."],
        estimates=[],
        recommendations=[],
        missing=[],
        sources=["get_cashflow"],
        tools_used=["get_cashflow"],
    )
    # Tentative d'hallucination : montant absent des faits
    merged = merge_llm_enrichment(
        base, {"summary": "Votre trésorerie est de 999999 € miraculeusement."}
    )
    assert "999999" not in merged.summary
    assert merged.summary == base.summary or "12 000" in merged.summary


def test_actions_proposed_with_confirmation_flags():
    db = make_assistant_db()
    org, _ = seed_assistant(db)
    tools = AssistantTools(db, org.id)
    answer = format_deterministic("unpaid", [tools.call("get_unpaid_invoices")])
    ids = {a.id for a in answer.actions}
    assert "open_dashboard" in ids
    assert "view_invoices" in ids
    confirm = [a for a in answer.actions if a.requires_confirmation]
    assert confirm  # create_reminder / prepare_report
