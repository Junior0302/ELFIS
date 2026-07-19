from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")

    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_tva: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="processing")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    anomalies: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    accounting_entry: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_extraction: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_contact_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    customer_contact_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisAnalysis(Base):
    """Rapport ELFIS AI versionné, lié à une facture et une organisation."""

    __tablename__ = "elfis_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(Integer, index=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    analysis_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    company_name: Mapped[str] = mapped_column(String(255), default="Mon Entreprise")
    siret: Mapped[str] = mapped_column(String(32), default="")
    vat_number: Mapped[str] = mapped_column(String(32), default="")
    default_vat_rate: Mapped[float] = mapped_column(Float, default=20.0)
    expense_account: Mapped[str] = mapped_column(String(32), default="606")
    vat_account: Mapped[str] = mapped_column(String(32), default="44566")
    supplier_account: Mapped[str] = mapped_column(String(32), default="401")
    accountant_firm: Mapped[str] = mapped_column(String(255), default="")
    accountant_email: Mapped[str] = mapped_column(String(255), default="")
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.85)


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    label: Mapped[str] = mapped_column(String(255), default="Compte courant")
    bank_name: Mapped[str] = mapped_column(String(255), default="")
    iban: Mapped[str] = mapped_column(String(64), default="")
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    booked_at: Mapped[str] = mapped_column(String(32))  # JJ-MM-AAAA
    label: Mapped[str] = mapped_column(String(512))
    amount: Mapped[float] = mapped_column(Float)  # + crédit / - débit
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    category: Mapped[str] = mapped_column(String(64), default="autre")
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
