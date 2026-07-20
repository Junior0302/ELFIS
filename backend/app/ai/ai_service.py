"""Service central ELFIS AI Engine."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.ai.ai_context import AIContext
from app.ai.ai_exceptions import (
    AIDisabledError,
    AINotFoundError,
    AIProviderError,
    AIUnknownTaskError,
    AIValidationError,
)
from app.ai.ai_models import ElfisAIExecution, ElfisAIUsage
from app.ai.ai_registry import AITaskRegistry, default_ai_registry
from app.ai.ai_repository import AIRepository
from app.ai.ai_schemas import AIExecutionRequest, AIExecutionResult, AIUsageSummary
from app.ai.ai_security import (
    assert_safe_ai_input,
    input_hash,
    limit_result,
    safe_ai_log_context,
    sanitize_ai_error,
)
from app.ai.ai_types import AIExecutionStatus, AIProviders, IMPLEMENTED_AI_TASKS
from app.ai.ai_usage import estimate_cost
from app.ai.providers.base import AIProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.config import settings
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames

logger = logging.getLogger(__name__)


def _as_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _publish(db: Session, event_name: str, execution: ElfisAIExecution, **extra: Any) -> None:
    payload = {
        "execution_id": execution.execution_id,
        "task_name": execution.task_name,
        "organization_id": execution.organization_id,
        "provider": execution.provider,
        "model": execution.model,
        "status": execution.status,
        "input_reference_type": execution.input_reference_type,
        "input_reference_id": execution.input_reference_id,
        "requires_review": execution.status == AIExecutionStatus.REQUIRES_REVIEW,
        "job_id": execution.job_id,
        "correlation_id": execution.correlation_id,
    }
    if "confidence" in extra and extra["confidence"] is not None:
        payload["confidence"] = extra["confidence"]
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=execution.organization_id or 0,
            aggregate_type="ai_execution",
            aggregate_id=execution.execution_id,
            payload=payload,
            metadata={"source": "ai_service"},
            correlation_id=_as_uuid(execution.correlation_id) or uuid.uuid4(),
            causation_id=_as_uuid(execution.source_event_id),
        ),
    )


class AIService:
    def __init__(
        self,
        db: Session,
        *,
        registry: AITaskRegistry | None = None,
        provider: AIProvider | None = None,
    ):
        self._db = db
        self._repo = AIRepository(db)
        self._registry = registry or default_ai_registry
        self._provider = provider

    def validate_task(self, task_name: str, task_version: int = 1) -> None:
        if task_name not in IMPLEMENTED_AI_TASKS:
            raise AIUnknownTaskError(task_name)
        if not self._registry.has(task_name, task_version):
            raise AIUnknownTaskError(task_name)

    def sanitize_input(self, data: dict[str, Any]) -> dict[str, Any]:
        return assert_safe_ai_input(data, max_bytes=settings.elfis_ai_max_input_bytes)

    def sanitize_output(self, data: dict[str, Any] | None) -> dict[str, Any] | None:
        return limit_result(data, max_bytes=settings.elfis_ai_max_output_bytes)

    def get_provider(self, name: str | None = None) -> AIProvider | None:
        if self._provider is not None:
            return self._provider
        provider = (name or settings.elfis_ai_provider or AIProviders.OPENAI).strip().lower()
        if provider == AIProviders.OPENAI:
            return OpenAIProvider()
        # Autres fournisseurs préparés — non implémentés
        raise AIProviderError(f"Fournisseur non implémenté en V1: {provider}")

    def resolve_model(self, task_name: str, model: str | None = None) -> str:
        if model:
            return model
        task = self._registry.get(task_name)
        if task.default_model:
            return task.default_model
        return settings.elfis_ai_default_model or settings.openai_chat_model

    def execute(self, request: AIExecutionRequest) -> AIExecutionResult:
        if not settings.elfis_ai_enabled:
            raise AIDisabledError()

        self.validate_task(request.task_name, request.task_version)
        input_data = self.sanitize_input(dict(request.input_data or {}))

        idem = (request.idempotency_key or "").strip() or None
        if idem:
            existing = self._repo.find_by_idempotency(idem)
            if existing:
                return self._to_result(existing, created=False, idempotent_reuse=True)

        provider_name = (request.provider or settings.elfis_ai_provider or AIProviders.OPENAI).strip()
        model = self.resolve_model(request.task_name, request.model)
        now = datetime.utcnow()
        execution = ElfisAIExecution(
            id=str(uuid.uuid4()),
            execution_id=str(uuid.uuid4()),
            organization_id=request.organization_id,
            user_id=request.user_id,
            task_name=request.task_name,
            task_version=request.task_version,
            provider=provider_name,
            model=model,
            status=AIExecutionStatus.PENDING,
            input_reference_type=request.input_reference_type,
            input_reference_id=request.input_reference_id,
            input_hash=input_hash(input_data),
            prompt_version=request.prompt_version,
            attempt_count=0,
            job_id=request.job_id,
            correlation_id=request.correlation_id or str(uuid.uuid4()),
            source_event_id=request.source_event_id,
            idempotency_key=idem,
            created_at=now,
            updated_at=now,
        )
        self._repo.save_execution(execution)
        _publish(self._db, EventNames.AI_EXECUTION_CREATED, execution)

        execution.status = AIExecutionStatus.PROCESSING
        execution.started_at = datetime.utcnow()
        execution.attempt_count = 1
        self._repo.save_execution(execution)
        _publish(self._db, EventNames.AI_EXECUTION_STARTED, execution)

        task = self._registry.get(request.task_name, request.task_version)
        context = AIContext(
            organization_id=request.organization_id,
            user_id=request.user_id,
            correlation_id=execution.correlation_id,
            job_id=request.job_id,
            execution_id=execution.execution_id,
            provider=provider_name,
            model=model,
        )

        # Quality check n'a pas besoin du provider LLM
        from app.ai.ai_types import AITaskNames

        provider: AIProvider | None = None
        if request.task_name != AITaskNames.DOCUMENT_QUALITY_CHECK:
            try:
                provider = self.get_provider(provider_name)
            except AIProviderError:
                provider = None  # fallback heuristique dans les tâches

        try:
            raw = task.execute(input_data, context, provider)
            usage_meta = raw.pop("_usage", {}) if isinstance(raw, dict) else {}
            validated = task.validate_output(raw)
            requires_review = bool(validated.get("requires_review")) or bool(
                validated.get("needs_review")
            )
            blocked = bool(validated.get("blocked"))
            confidence = validated.get("confidence")
            if confidence is not None:
                try:
                    confidence = float(confidence)
                except (TypeError, ValueError):
                    confidence = None

            if blocked:
                status = AIExecutionStatus.BLOCKED
            elif requires_review:
                status = AIExecutionStatus.REQUIRES_REVIEW
            else:
                status = AIExecutionStatus.COMPLETED

            limited = self.sanitize_output(validated)
            inp = usage_meta.get("input_tokens")
            out = usage_meta.get("output_tokens")
            total = usage_meta.get("total_tokens")
            cost = estimate_cost(
                provider=provider_name, model=model, input_tokens=inp, output_tokens=out
            )
            latency = usage_meta.get("latency_ms")

            execution.status = status
            execution.result = limited
            execution.result_schema_version = 1
            execution.input_tokens = inp
            execution.output_tokens = out
            execution.total_tokens = total
            execution.estimated_cost = cost
            execution.latency_ms = latency
            execution.completed_at = datetime.utcnow()
            execution.last_error = None
            self._repo.save_execution(execution)
            self._record_usage(execution)

            if status == AIExecutionStatus.REQUIRES_REVIEW:
                _publish(
                    self._db,
                    EventNames.AI_EXECUTION_REQUIRES_REVIEW,
                    execution,
                    confidence=confidence,
                )
            else:
                _publish(
                    self._db,
                    EventNames.AI_EXECUTION_COMPLETED,
                    execution,
                    confidence=confidence,
                )
            _publish(self._db, EventNames.AI_USAGE_RECORDED, execution)

            logger.info(
                "ai_execution_done",
                extra=safe_ai_log_context(
                    execution_id=execution.execution_id,
                    task_name=execution.task_name,
                    organization_id=execution.organization_id,
                    provider=execution.provider,
                    model=execution.model,
                    status=execution.status,
                    latency_ms=execution.latency_ms,
                    input_tokens=execution.input_tokens,
                    output_tokens=execution.output_tokens,
                    total_tokens=execution.total_tokens,
                    estimated_cost=float(cost) if cost is not None else None,
                    job_id=execution.job_id,
                    correlation_id=execution.correlation_id,
                ),
            )
            return self._to_result(
                execution, created=True, confidence=confidence, requires_review=requires_review
            )

        except AIValidationError as exc:
            return self._fail(execution, exc.message, event=EventNames.AI_EXECUTION_FAILED)
        except Exception as exc:
            msg = sanitize_ai_error(str(exc)) or "erreur IA"
            return self._fail(execution, msg, event=EventNames.AI_EXECUTION_FAILED)

    def _fail(self, execution: ElfisAIExecution, message: str, *, event: str) -> AIExecutionResult:
        execution.status = AIExecutionStatus.FAILED
        execution.failed_at = datetime.utcnow()
        execution.last_error = sanitize_ai_error(message)
        self._repo.save_execution(execution)
        _publish(self._db, event, execution)
        logger.error(
            "ai_execution_failed",
            extra=safe_ai_log_context(
                execution_id=execution.execution_id,
                task_name=execution.task_name,
                status=execution.status,
                organization_id=execution.organization_id,
            ),
        )
        return self._to_result(execution, created=True)

    def _record_usage(self, execution: ElfisAIExecution) -> None:
        row = ElfisAIUsage(
            id=str(uuid.uuid4()),
            organization_id=execution.organization_id,
            user_id=execution.user_id,
            execution_id=execution.execution_id,
            provider=execution.provider,
            model=execution.model,
            task_name=execution.task_name,
            input_tokens=execution.input_tokens,
            output_tokens=execution.output_tokens,
            total_tokens=execution.total_tokens,
            estimated_cost=execution.estimated_cost,
            currency=execution.currency or "USD",
            request_date=date.today(),
            created_at=datetime.utcnow(),
        )
        self._repo.create_usage(row)

    def get_execution(self, execution_id: str) -> ElfisAIExecution:
        row = self._repo.find_execution(execution_id)
        if not row:
            raise AINotFoundError()
        return row

    def list_executions(self, **kwargs: Any):
        return self._repo.list_executions(**kwargs)

    def get_usage(self, **kwargs: Any):
        return self._repo.list_usage(**kwargs)

    def estimate_usage(
        self, *, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> Decimal | None:
        return estimate_cost(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _to_result(
        self,
        execution: ElfisAIExecution,
        *,
        created: bool,
        idempotent_reuse: bool = False,
        confidence: float | None = None,
        requires_review: bool | None = None,
    ) -> AIExecutionResult:
        result = execution.result if isinstance(execution.result, dict) else None
        if confidence is None and result:
            try:
                confidence = float(result.get("confidence")) if result.get("confidence") is not None else None
            except (TypeError, ValueError):
                confidence = None
        if requires_review is None:
            requires_review = execution.status == AIExecutionStatus.REQUIRES_REVIEW or bool(
                result and (result.get("requires_review") or result.get("needs_review"))
            )
        cost = float(execution.estimated_cost) if execution.estimated_cost is not None else None
        return AIExecutionResult(
            execution_id=execution.execution_id,
            status=execution.status,
            task_name=execution.task_name,
            provider=execution.provider,
            model=execution.model,
            result=result,
            requires_review=bool(requires_review),
            confidence=confidence,
            usage=AIUsageSummary(
                input_tokens=execution.input_tokens,
                output_tokens=execution.output_tokens,
                total_tokens=execution.total_tokens,
                estimated_cost=cost,
                currency=execution.currency or "USD",
            ),
            latency_ms=execution.latency_ms,
            created=created,
            idempotent_reuse=idempotent_reuse,
        )
