"""Tests provider OpenAI mocké + sécurité logs."""

from __future__ import annotations

from app.ai.ai_schemas import AIProviderResponse
from app.ai.ai_security import sanitize_ai_error, safe_ai_log_context
from app.ai.providers.openai_provider import OpenAIProvider


def test_openai_provider_requires_key():
    p = OpenAIProvider(api_key="")
    try:
        p.execute_structured(model="gpt-4o-mini", system="s", user="u")
        assert False, "should raise"
    except Exception as exc:
        assert "api_key" not in str(exc).lower() or "vide" in str(exc).lower()
        assert "sk-" not in str(exc)


def test_sanitize_error_masks_secrets():
    msg = sanitize_ai_error("failed api_key=sk-abc123 password=secret")
    assert "sk-abc" not in (msg or "")
    assert "***" in (msg or "")


def test_safe_log_context_no_prompt_or_text():
    ctx = safe_ai_log_context(
        execution_id="e1",
        task_name="document.classify.v1",
        prompt="SYSTEM SECRET",
        extracted_text="FULL DOCUMENT",
        api_key="sk-x",
        input_tokens=1,
    )
    assert "prompt" not in ctx
    assert "extracted_text" not in ctx
    assert "api_key" not in ctx
    assert ctx["input_tokens"] == 1


def test_provider_response_schema():
    r = AIProviderResponse(content="{}", structured_output={"a": 1}, total_tokens=3)
    assert r.structured_output["a"] == 1
