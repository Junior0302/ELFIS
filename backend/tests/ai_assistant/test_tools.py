"""Tests outils IA + détection d'intention."""

from __future__ import annotations

from app.ai_assistant.tools import INTENT_TOOLS, AssistantTools, detect_intent
from tests.ai_assistant.helpers import make_assistant_db, seed_assistant


def test_detect_intent_routing():
    assert detect_intent("Quel est l'état de ma trésorerie ?") == "cashflow"
    assert detect_intent("Quels clients sont en retard ?") == "unpaid"
    assert detect_intent("Où en est ma TVA ?") == "vat"
    assert detect_intent("Pourquoi ma marge baisse ?") == "expenses"
    assert detect_intent("Documents à traiter") == "documents"
    assert detect_intent("Cherche transaction loyer") == "transactions"
    assert detect_intent("Quel est mon health score ?") == "health"
    assert detect_intent("Que peux-tu faire ?") == "help"
    assert detect_intent("Résume mon activité") == "overview"


def test_all_tools_are_callable_and_return_facts():
    db = make_assistant_db()
    org, _ = seed_assistant(db)
    tools = AssistantTools(db, org.id)

    names = tools.names()
    assert "get_cashflow" in names
    assert set(names) >= {
        "get_cashflow",
        "get_unpaid_invoices",
        "get_vat",
        "get_expenses",
        "get_documents",
        "search_transactions",
        "get_kpis",
        "get_alerts",
        "get_health_score",
        "get_sync_status",
    }

    cash = tools.call("get_cashflow")
    assert cash.ok
    assert cash.data["treasury"] == 12000.0
    assert "forecast" in cash.data

    unpaid = tools.call("get_unpaid_invoices")
    assert unpaid.ok
    assert unpaid.data["overdue_count"] == 1

    vat = tools.call("get_vat")
    assert vat.ok
    assert vat.data["vat_estimated"] == 2560.0

    expenses = tools.call("get_expenses")
    assert expenses.ok
    assert expenses.data["expenses"] == 4000.0

    docs = tools.call("get_documents")
    assert docs.ok
    assert docs.data["documents_to_process"] == 1

    txs = tools.call("search_transactions", q="LOYER")
    assert txs.ok
    assert txs.data["total"] >= 1

    assert tools.call("get_kpis").ok
    assert tools.call("get_alerts").ok
    assert tools.call("get_health_score").ok
    assert tools.call("get_sync_status").ok


def test_unknown_tool_fails_gracefully():
    db = make_assistant_db()
    org, _ = seed_assistant(db)
    result = AssistantTools(db, org.id).call("invent_numbers")
    assert result.ok is False
    assert "inconnu" in (result.error or "").lower()


def test_intent_tools_map_is_complete():
    for tools in INTENT_TOOLS.values():
        assert isinstance(tools, list)
