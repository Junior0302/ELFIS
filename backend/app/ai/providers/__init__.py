"""Providers IA."""

from app.ai.providers.base import AIProvider
from app.ai.providers.openai_provider import OpenAIProvider

__all__ = ["AIProvider", "OpenAIProvider"]
