"""Provider OpenAI — réutilise OPENAI_API_KEY / openai_chat_model."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.ai.ai_exceptions import AIProviderError
from app.ai.ai_schemas import AIProviderResponse
from app.ai.ai_security import sanitize_ai_error
from app.ai.providers.base import AIProvider
from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    provider_name = "openai"

    def __init__(self, *, api_key: str | None = None, timeout_seconds: int | None = None):
        self._api_key = (api_key if api_key is not None else settings.openai_api_key) or ""
        self._timeout = timeout_seconds or settings.elfis_ai_request_timeout_seconds

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "configured": bool(self._api_key),
            "default_model": settings.elfis_ai_default_model or settings.openai_chat_model,
        }

    def execute_text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
    ) -> AIProviderResponse:
        return self._chat(
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            json_mode=False,
        )

    def execute_structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
    ) -> AIProviderResponse:
        return self._chat(
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            json_mode=True,
        )

    def _chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        json_mode: bool,
    ) -> AIProviderResponse:
        if not self._api_key:
            raise AIProviderError("OpenAI non configuré (OPENAI_API_KEY vide)")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderError("package openai indisponible") from exc

        client = OpenAI(api_key=self._api_key, timeout=self._timeout)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        started = time.monotonic()
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise AIProviderError(sanitize_ai_error(str(exc)) or "erreur provider") from None

        latency_ms = int((time.monotonic() - started) * 1000)
        content = (response.choices[0].message.content or "") if response.choices else ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = int(input_tokens) + int(output_tokens)

        structured = None
        if json_mode and content:
            try:
                structured = json.loads(content)
            except json.JSONDecodeError:
                structured = None

        return AIProviderResponse(
            content=content,
            structured_output=structured if isinstance(structured, dict) else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            provider_request_id=getattr(response, "id", None),
        )
