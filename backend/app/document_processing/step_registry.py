"""Registre pipelines + handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.config import settings
from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingValidationError
from app.document_processing.types import (
    PIPELINE_BASIC_V1,
    PIPELINE_BUSINESS_VALIDATION_V1,
    PIPELINE_CLASSIFICATION_V1,
    PIPELINE_EXTRACTION_V1,
    PIPELINE_OCR_V1,
    STEP_CLASSIFY,
    STEP_FINALIZE,
    STEP_FINALIZE_BUSINESS_VALIDATION,
    STEP_FINALIZE_EXTRACTION,
    STEP_FINALIZE_OCR_RESULT,
    STEP_INSPECT,
    STEP_LOAD_EXTRACTION_CONTENT,
    STEP_LOAD_EXTRACTION_SOURCE,
    STEP_NOOP,
    STEP_PERFORM_BUSINESS_VALIDATION,
    STEP_PERFORM_EXTRACTION,
    STEP_PERFORM_OCR,
    STEP_PERSIST_CLASSIFICATION,
    STEP_PERSIST_EXTRACTION_ARTIFACT,
    STEP_PERSIST_OCR_ARTIFACT,
    STEP_PERSIST_VALIDATION_ARTIFACT,
    STEP_PREPARE_OCR_INPUT,
    STEP_RESOLVE_EFFECTIVE_TYPE,
    STEP_SELECT_BUSINESS_RULE_SET,
    STEP_SELECT_EFFECTIVE_EXTRACTION,
    STEP_SELECT_EXTRACTION_SCHEMA,
    STEP_SELECT_EXTRACTION_SOURCE,
    STEP_SELECT_OCR_PROVIDER,
    STEP_VALIDATE,
    STEP_VALIDATE_EXTRACTION,
)


class ProcessingStepHandler(Protocol):
    step_key: str

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult: ...


@dataclass(frozen=True)
class PipelineStepDef:
    key: str
    sequence: int
    required: bool = True
    timeout_seconds: int = 120
    max_attempts: int = 3


@dataclass(frozen=True)
class PipelineDef:
    key: str
    steps: tuple[PipelineStepDef, ...]


class DocumentProcessingPipelineRegistry:
    def __init__(self) -> None:
        self._pipelines: dict[str, PipelineDef] = {}
        self._handlers: dict[str, ProcessingStepHandler] = {}

    def register_pipeline(self, pipeline: PipelineDef) -> None:
        self._pipelines[pipeline.key] = pipeline

    def register_handler(self, handler: ProcessingStepHandler) -> None:
        self._handlers[handler.step_key] = handler

    def get_pipeline(self, key: str) -> PipelineDef:
        pipe = self._pipelines.get(key)
        if not pipe:
            raise ProcessingValidationError("pipeline_unknown", f"Pipeline inconnu: {key}")
        return pipe

    def get_handler(self, step_key: str) -> ProcessingStepHandler:
        handler = self._handlers.get(step_key)
        if not handler:
            raise ProcessingValidationError("handler_missing", f"Handler absent: {step_key}")
        return handler

    def known_pipelines(self) -> list[str]:
        return sorted(self._pipelines.keys())


def build_default_registry() -> DocumentProcessingPipelineRegistry:
    from app.document_processing.steps.classify_step import ClassifyDocumentStep
    from app.document_processing.steps.extraction_steps import (
        FinalizeExtractionResultStep,
        LoadExtractionSourceStep,
        PerformStructuredExtractionStep,
        PersistExtractionArtifactStep,
        ResolveEffectiveDocumentTypeStep,
        SelectExtractionSchemaStep,
        SelectExtractionSourceStep,
        ValidateExtractionSchemaStep,
    )
    from app.document_processing.steps.finalize_step import FinalizeProcessingStep
    from app.document_processing.steps.inspect_step import InspectStorageMetadataStep
    from app.document_processing.steps.noop_step import NoopProcessingStep
    from app.document_processing.steps.ocr_steps import (
        FinalizeOCRResultStep,
        PerformOCRStep,
        PersistOCRArtifactStep,
        PrepareOCRInputStep,
        SelectOCRProviderStep,
    )
    from app.document_processing.steps.persist_classification_step import PersistClassificationStep
    from app.document_processing.steps.validate_step import ValidateDocumentAvailableStep
    from app.document_processing.steps.validation_steps import (
        FinalizeBusinessValidationStep,
        LoadExtractionContentStep,
        PerformBusinessValidationStep,
        PersistValidationArtifactStep,
        SelectBusinessRuleSetStep,
        SelectEffectiveExtractionStep,
    )

    reg = DocumentProcessingPipelineRegistry()
    default_timeout = int(
        getattr(settings, "document_processing_default_step_timeout_seconds", 120) or 120
    )
    max_attempts = int(getattr(settings, "document_processing_max_attempts", 3) or 3)
    ocr_timeout = int(getattr(settings, "document_ocr_max_processing_seconds", 180) or 180)
    extr_timeout = int(getattr(settings, "document_extraction_timeout_seconds", 120) or 120)
    bv_timeout = int(getattr(settings, "document_business_validation_timeout_seconds", 120) or 120)

    reg.register_pipeline(
        PipelineDef(
            key=PIPELINE_BASIC_V1,
            steps=(
                PipelineStepDef(STEP_VALIDATE, 1, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_INSPECT, 2, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_NOOP, 3, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE, 4, True, default_timeout, max_attempts),
            ),
        )
    )
    reg.register_pipeline(
        PipelineDef(
            key=PIPELINE_CLASSIFICATION_V1,
            steps=(
                PipelineStepDef(STEP_VALIDATE, 1, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_INSPECT, 2, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_CLASSIFY, 3, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_PERSIST_CLASSIFICATION, 4, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE, 5, True, default_timeout, max_attempts),
            ),
        )
    )
    reg.register_pipeline(
        PipelineDef(
            key=PIPELINE_OCR_V1,
            steps=(
                PipelineStepDef(STEP_VALIDATE, 1, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_INSPECT, 2, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_SELECT_OCR_PROVIDER, 3, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_PREPARE_OCR_INPUT, 4, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_PERFORM_OCR, 5, True, ocr_timeout, max_attempts),
                PipelineStepDef(STEP_PERSIST_OCR_ARTIFACT, 6, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE_OCR_RESULT, 7, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE, 8, True, default_timeout, max_attempts),
            ),
        )
    )
    reg.register_pipeline(
        PipelineDef(
            key=PIPELINE_EXTRACTION_V1,
            steps=(
                PipelineStepDef(STEP_VALIDATE, 1, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_RESOLVE_EFFECTIVE_TYPE, 2, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_SELECT_EXTRACTION_SCHEMA, 3, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_SELECT_EXTRACTION_SOURCE, 4, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_LOAD_EXTRACTION_SOURCE, 5, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_PERFORM_EXTRACTION, 6, True, extr_timeout, max_attempts),
                PipelineStepDef(STEP_VALIDATE_EXTRACTION, 7, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_PERSIST_EXTRACTION_ARTIFACT, 8, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE_EXTRACTION, 9, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE, 10, True, default_timeout, max_attempts),
            ),
        )
    )
    reg.register_pipeline(
        PipelineDef(
            key=PIPELINE_BUSINESS_VALIDATION_V1,
            steps=(
                PipelineStepDef(STEP_VALIDATE, 1, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_RESOLVE_EFFECTIVE_TYPE, 2, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_SELECT_EFFECTIVE_EXTRACTION, 3, True, bv_timeout, max_attempts),
                PipelineStepDef(STEP_LOAD_EXTRACTION_CONTENT, 4, True, bv_timeout, max_attempts),
                PipelineStepDef(STEP_SELECT_BUSINESS_RULE_SET, 5, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_PERFORM_BUSINESS_VALIDATION, 6, True, bv_timeout, max_attempts),
                PipelineStepDef(STEP_PERSIST_VALIDATION_ARTIFACT, 7, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE_BUSINESS_VALIDATION, 8, True, default_timeout, max_attempts),
                PipelineStepDef(STEP_FINALIZE, 9, True, default_timeout, max_attempts),
            ),
        )
    )
    for h in (
        ValidateDocumentAvailableStep(),
        InspectStorageMetadataStep(),
        NoopProcessingStep(),
        ClassifyDocumentStep(),
        PersistClassificationStep(),
        SelectOCRProviderStep(),
        PrepareOCRInputStep(),
        PerformOCRStep(),
        PersistOCRArtifactStep(),
        FinalizeOCRResultStep(),
        ResolveEffectiveDocumentTypeStep(),
        SelectExtractionSchemaStep(),
        SelectExtractionSourceStep(),
        LoadExtractionSourceStep(),
        PerformStructuredExtractionStep(),
        ValidateExtractionSchemaStep(),
        PersistExtractionArtifactStep(),
        FinalizeExtractionResultStep(),
        SelectEffectiveExtractionStep(),
        LoadExtractionContentStep(),
        SelectBusinessRuleSetStep(),
        PerformBusinessValidationStep(),
        PersistValidationArtifactStep(),
        FinalizeBusinessValidationStep(),
        FinalizeProcessingStep(),
    ):
        reg.register_handler(h)
    return reg


_DEFAULT: DocumentProcessingPipelineRegistry | None = None


def get_pipeline_registry() -> DocumentProcessingPipelineRegistry:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = build_default_registry()
    return _DEFAULT


def reset_pipeline_registry_for_tests() -> None:
    global _DEFAULT
    _DEFAULT = None
