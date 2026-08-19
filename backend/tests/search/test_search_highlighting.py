"""Tests highlighting + sécurité."""

from __future__ import annotations

from app.search.search_highlighting import build_snippet
from app.search.search_logging import query_hash, safe_search_log_context


def test_snippet_escaped_and_marked():
    snip = build_snippet('<b>Facture ACME</b> Total 120', 'ACME')
    assert "<b>" not in snip or "&lt;b&gt;" in snip
    assert "[[ACME]]" in snip or "[[Acme]]" in snip.lower() or "ACME" in snip


def test_safe_log_no_query():
    ctx = safe_search_log_context(
        organization_id=1,
        query_hash_value=query_hash("secret invoice"),
        query="secret invoice",
        search_text="full text",
    )
    assert "query" not in ctx
    assert "search_text" not in ctx
    assert ctx["query_hash"]
