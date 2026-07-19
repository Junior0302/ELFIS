from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ─── AUTH & ORGANISATION ─────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    firebase_uid: Mapped[str] = mapped_column(String(128), default="", index=True)
    phone: Mapped[str] = mapped_column(String(64), default="")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    legal_name: Mapped[str] = mapped_column(String(255), default="")
    siren: Mapped[str] = mapped_column(String(32), default="")
    vat_number: Mapped[str] = mapped_column(String(64), default="")
    country: Mapped[str] = mapped_column(String(8), default="FR")
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    logo: Mapped[str] = mapped_column(String(512), default="")
    industry: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    postal_code: Mapped[str] = mapped_column(String(32), default="")
    city: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    iban: Mapped[str] = mapped_column(String(64), default="")
    bic: Mapped[str] = mapped_column(String(32), default="")
    share_capital: Mapped[str] = mapped_column(String(64), default="")
    legal_form: Mapped[str] = mapped_column(String(64), default="")
    legal_mentions: Mapped[str] = mapped_column(Text, default="")
    primary_color: Mapped[str] = mapped_column(String(16), default="#0B3D2E")
    secondary_color: Mapped[str] = mapped_column(String(16), default="#E7F2EC")
    subscription_plan: Mapped[str] = mapped_column(String(64), default="starter")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    permissions: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    description: Mapped[str] = mapped_column(String(255), default="")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    module: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(String(255), default="")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    # active | suspended | removed
    invited_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(64), default="employe")
    permissions_json: Mapped[str] = mapped_column(Text, default="[]")
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending | accepted | expired | cancelled | refused
    invited_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TeamNotification(Base):
    __tablename__ = "team_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(64), default="info")
    title: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Company(Base):
    """Filiale / établissement sous une organisation."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    parent_company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(8), default="FR")
    currency: Mapped[str] = mapped_column(String(8), default="EUR")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    plan: Mapped[str] = mapped_column(String(64), default="starter")
    status: Mapped[str] = mapped_column(String(32), default="active")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trial_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_source_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trial_eligibility_status: Mapped[str] = mapped_column(
        String(32), default="eligible"
    )  # eligible|already_used|blocked|admin_granted
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    past_due_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    access_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payment_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_payment_failure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_payment_succeeded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    admin_revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    admin_revoked_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_revoked_reason_public: Mapped[str] = mapped_column(Text, default="")
    admin_revoked_reason_internal: Mapped[str] = mapped_column(Text, default="")


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    stripe_object_id: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="processed")  # received|processed|failed
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    payload_hash: Mapped[str] = mapped_column(String(64), default="")
    last_error: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SubscriptionConsent(Base):
    __tablename__ = "subscription_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consent_type: Mapped[str] = mapped_column(String(64), default="trial_checkout")
    terms_version: Mapped[str] = mapped_column(String(32), default="v1")
    price_amount: Mapped[int] = mapped_column(Integer, default=1900)  # centimes
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    trial_days: Mapped[int] = mapped_column(Integer, default=14)
    automatic_renewal_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    checkout_session_id: Mapped[str] = mapped_column(String(255), default="")


class SubscriptionNotification(Base):
    __tablename__ = "subscription_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notification_type: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(32), default="email")  # email|in_app
    recipient: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|sent|failed
    provider_message_id: Mapped[str] = mapped_column(String(255), default="")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    deduplication_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AIAgent(Base):
    __tablename__ = "ai_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    status: Mapped[str] = mapped_column(String(32), default="active")


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(255))
    module: Mapped[str] = mapped_column(String(64), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── MODULE 4 — FACTURATION (clients / ventes) ───────────────────


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    vat_number: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CatalogItem(Base):
    """Produit ou service du catalogue commercial."""

    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32), default="produit")  # produit|service
    unit: Mapped[str] = mapped_column(String(64), default="unité")
    unit_price_ht: Mapped[float] = mapped_column(Float, default=0.0)
    vat_rate: Mapped[float] = mapped_column(Float, default=20.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CommercialActivity(Base):
    """Activité commerciale (vente, service, rdv, suivi)."""

    __tablename__ = "commercial_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32), default="rdv")  # vente|service|rdv|suivi
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planifie")  # planifie|fait|annule
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SalesDocument(Base):
    """Devis / Facture / Avoir émis (Module 4)."""

    __tablename__ = "sales_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(32), default="facture")  # devis|facture|avoir
    number: Mapped[str] = mapped_column(String(64), index=True)
    issue_date: Mapped[str] = mapped_column(String(32))
    due_date: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    # draft | sent | accepted | refused | paid | partial | overdue | cancelled
    customer_name: Mapped[str] = mapped_column(String(255), default="")
    customer_email: Mapped[str] = mapped_column(String(255), default="")
    amount_ht: Mapped[float] = mapped_column(Float, default=0.0)
    amount_tva: Mapped[float] = mapped_column(Float, default=0.0)
    amount_ttc: Mapped[float] = mapped_column(Float, default=0.0)
    vat_rate: Mapped[float] = mapped_column(Float, default=20.0)
    lines_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    signature_status: Mapped[str] = mapped_column(String(32), default="none")  # none|pending|signed
    converted_from_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_documents.id"), index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    channel: Mapped[str] = mapped_column(String(32), default="email")
    message: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="sent")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_documents.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(64), default="virement")
    paid_at: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentEmailLog(Base):
    __tablename__ = "document_email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_documents.id"), index=True, nullable=True
    )
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    document_type: Mapped[str] = mapped_column(String(32), default="")
    sent_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recipient: Mapped[str] = mapped_column(String(255), default="")
    recipient_email: Mapped[str] = mapped_column(String(255), default="")
    cc_email: Mapped[str] = mapped_column(String(255), default="")
    bcc_email: Mapped[str] = mapped_column(String(255), default="")
    sender_name: Mapped[str] = mapped_column(String(255), default="")
    sender_email: Mapped[str] = mapped_column(String(255), default="")
    reply_to_email: Mapped[str] = mapped_column(String(255), default="")
    subject: Mapped[str] = mapped_column(String(255), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    provider_message_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    email_connection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="preparing")
    # preparing|queued|sent|delivered|opened|bounced|blocked|failed
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OrganizationEmailSettings(Base):
    """Paramètres d'expédition par organisation (identité visible, pas de clé Brevo)."""

    __tablename__ = "organization_email_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    sender_mode: Mapped[str] = mapped_column(String(32), default="platform")  # platform|custom_sender
    sender_name: Mapped[str] = mapped_column(String(255), default="")
    reply_to_email: Mapped[str] = mapped_column(String(255), default="")
    reply_to_name: Mapped[str] = mapped_column(String(255), default="")
    cc_email: Mapped[str] = mapped_column(String(255), default="")
    bcc_email: Mapped[str] = mapped_column(String(255), default="")
    invoice_default_subject: Mapped[str] = mapped_column(String(255), default="")
    invoice_default_message: Mapped[str] = mapped_column(Text, default="")
    quote_default_subject: Mapped[str] = mapped_column(String(255), default="")
    quote_default_message: Mapped[str] = mapped_column(Text, default="")
    email_signature: Mapped[str] = mapped_column(Text, default="")
    send_copy_to_organization: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_sender_email: Mapped[str] = mapped_column(String(255), default="")
    custom_sender_status: Mapped[str] = mapped_column(String(32), default="not_configured")
    # not_configured|pending|verified|rejected|disabled
    custom_sender_provider_id: Mapped[str] = mapped_column(String(255), default="")
    custom_domain: Mapped[str] = mapped_column(String(255), default="")
    custom_domain_status: Mapped[str] = mapped_column(String(32), default="not_configured")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OrganizationEmailConnection(Base):
    """Boîte mail d’expédition appartenant à l’organisation (OAuth / SMTP / platform)."""

    __tablename__ = "organization_email_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="platform")
    # platform | google | microsoft | custom_smtp
    email_address: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="connected")
    # connected | expired | revoked | error | disconnected
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    connected_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_account_id: Mapped[str] = mapped_column(String(255), default="")
    encrypted_access_token: Mapped[str] = mapped_column(Text, default="")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    encrypted_smtp_password: Mapped[str] = mapped_column(Text, default="")
    smtp_host: Mapped[str] = mapped_column(String(255), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    smtp_username: Mapped[str] = mapped_column(String(255), default="")
    smtp_security: Mapped[str] = mapped_column(String(16), default="starttls")
    # starttls | ssl | none
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_code: Mapped[str] = mapped_column(String(64), default="")
    last_error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProfessionalEmail(Base):
    """Adresse e-mail professionnelle ELFIS Core (@elfis-core.com) liée à un utilisateur."""

    __tablename__ = "professional_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    suggested_email: Mapped[str] = mapped_column(String(255), default="")
    provider: Mapped[str] = mapped_column(String(32), default="brevo")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | creating | active | suspended | rejected
    request_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    activated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ─── CONTACTS (clients / fournisseurs / prospects) ───────────────


class Contact(Base):
    """Contact CRM unifié (client, fournisseur, prospect)."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    contact_type: Mapped[str] = mapped_column(String(32), default="customer", index=True)
    # customer | supplier | prospect | customer_and_supplier
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    company_name: Mapped[str] = mapped_column(String(255), default="")
    trade_name: Mapped[str] = mapped_column(String(255), default="")
    first_name: Mapped[str] = mapped_column(String(128), default="")
    last_name: Mapped[str] = mapped_column(String(128), default="")

    siren: Mapped[str] = mapped_column(String(16), default="", index=True)
    siret: Mapped[str] = mapped_column(String(20), default="", index=True)
    vat_number: Mapped[str] = mapped_column(String(64), default="", index=True)

    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    phone: Mapped[str] = mapped_column(String(64), default="")

    address_line_1: Mapped[str] = mapped_column(String(255), default="")
    address_line_2: Mapped[str] = mapped_column(String(255), default="")
    postal_code: Mapped[str] = mapped_column(String(32), default="")
    city: Mapped[str] = mapped_column(String(128), default="")
    country: Mapped[str] = mapped_column(String(64), default="France")

    iban: Mapped[str] = mapped_column(String(64), default="")
    bic: Mapped[str] = mapped_column(String(32), default="")
    payment_terms: Mapped[str] = mapped_column(String(255), default="")
    payment_method: Mapped[str] = mapped_column(String(128), default="")

    source: Mapped[str] = mapped_column(String(64), default="manual")
    # manual | document_extraction | import
    source_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContactSuggestion(Base):
    """Suggestion de contact issue d’un document — confirmation utilisateur requise."""

    __tablename__ = "contact_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(32), default="supplier")  # supplier | customer
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | accepted | linked | ignored | rejected
    suggested_contact_type: Mapped[str] = mapped_column(String(32), default="supplier")
    suggested_action: Mapped[str] = mapped_column(String(64), default="create_contact")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extracted_data_json: Mapped[str] = mapped_column(Text, default="{}")
    duplicates_json: Mapped[str] = mapped_column(Text, default="[]")
    matched_contact_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_fields_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
