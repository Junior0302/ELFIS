"""Enums Document Analysis."""

from __future__ import annotations

from enum import Enum


class AnalysisReportStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentClass(str, Enum):
    INVOICE = "invoice"
    QUOTE = "quote"
    CREDIT_NOTE = "credit_note"
    BANK_STATEMENT = "bank_statement"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"


class LanguageCode(str, Enum):
    FR = "fr"
    EN = "en"
    DE = "de"
    ES = "es"
    IT = "it"
    NL = "nl"
    UNKNOWN = "unknown"
