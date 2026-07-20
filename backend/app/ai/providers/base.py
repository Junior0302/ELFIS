"""Interface fournisseur IA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.ai.ai_schemas import AIProviderResponse


class AIProvider(ABC):
    provider_name: str

    @abstractmethod
    def execute_text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
    ) -> AIProviderResponse:
        raise NotImplementedError

    @abstractmethod
    def execute_structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
    ) -> AIProviderResponse:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError
