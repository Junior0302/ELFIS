from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, text
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
    # Banking Platform V1 : rattachement à une connexion fournisseur
    connection_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="manual")
    external_id: Mapped[str] = mapped_column(String(128), default="")
    label: Mapped[str] = mapped_column(String(255), default="Compte courant")
    bank_name: Mapped[str] = mapped_column(String(255), default="")
    iban: Mapped[str] = mapped_column(String(64), default="")
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    # BANK-2 — interne uniquement ; jamais exposé en clair par l'API banking
    account_type: Mapped[str] = mapped_column(String(32), default="other")
    available_balance: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    balance_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        # BANK-3.1 — identité provider uniquement. external_id vide = observations distinctes.
        Index(
            "uq_bank_transactions_account_external_id",
            "account_id",
            "external_id",
            unique=True,
            postgresql_where=text("btrim(COALESCE(external_id, '')) <> ''"),
            sqlite_where=text("trim(COALESCE(external_id, '')) <> ''"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    booked_at: Mapped[str] = mapped_column(String(32))  # ISO YYYY-MM-DD (legacy JJ-MM-AAAA possible)
    value_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    label: Mapped[str] = mapped_column(String(512))
    amount: Mapped[float] = mapped_column(Float)  # + crédit / - débit
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    category: Mapped[str] = mapped_column(String(64), default="autre")
    # Banking Platform V1 : statut normalisé + fournisseur d'origine
    status: Mapped[str] = mapped_column(String(16), default="booked")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
