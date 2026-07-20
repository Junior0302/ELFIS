"""Tests sécurité AI."""

from __future__ import annotations

import pytest

from app.ai.ai_exceptions import AIValidationError
from app.ai.ai_security import assert_safe_ai_input, sanitize_ai_error, safe_ai_log_context


def test_refuse_jwt_password_keys():
    with pytest.raises(AIValidationError):
        assert_safe_ai_input({"jwt": "eyJhbGciOi"}, max_bytes=1000)
    with pytest.raises(AIValidationError):
        assert_safe_ai_input({"password": "x"}, max_bytes=1000)


def test_payload_too_large():
    with pytest.raises(AIValidationError):
        assert_safe_ai_input({"extracted_text": "x" * 5000}, max_bytes=100)


def test_no_api_key_in_logs():
    ctx = safe_ai_log_context(execution_id="1", api_key="sk-live", result={"full": True})
    assert "api_key" not in ctx
    assert "result" not in ctx
    assert "sk-live" not in sanitize_ai_error("err api_key=sk-live")
