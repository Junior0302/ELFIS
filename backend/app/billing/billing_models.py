"""Modèles SQLAlchemy — Billing Subscriptions / Entitlements / Quotas."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisBillingPlan(Base):
    __tablename__ = "elfis_billing_plans"
    __table_args__ = (
        UniqueConstraint("plan_id", name="uq_elfis_billing_plan_id"),
        UniqueConstraint("plan_code", name="uq_elfis_billing_plan_code"),
        CheckConstraint(
            "billing_interval IS NULL OR billing_interval IN ('month','year','one_time','none')",
            name="ck_elfis_billing_interval",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    plan_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    plan_code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(8), nullable=False, default="EUR")
    price_amount = Column(Numeric(12, 2), nullable=False, default=0)
    billing_interval = Column(String(16), nullable=True)
    trial_days = Column(Integer, nullable=False, default=0)
    stripe_product_id = Column(String(128), nullable=True)
    stripe_price_id = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_public = Column(Boolean, nullable=False, default=False, index=True)
    features = Column(JSON, nullable=False, default=dict)
    quotas = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisSubscription(Base):
    __tablename__ = "elfis_subscriptions"
    __table_args__ = (
        UniqueConstraint("subscription_id", name="uq_elfis_subscription_id"),
        CheckConstraint(
            "status IN ("
            "'incomplete','trialing','active','past_due','unpaid',"
            "'paused','cancelled','expired','suspended'"
            ")",
            name="ck_elfis_subscription_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    subscription_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    plan_id = Column(String(36), nullable=False)
    status = Column(String(32), nullable=False, index=True)
    source = Column(String(32), nullable=False, default="stripe")
    legacy_subscription_id = Column(Integer, nullable=True)
    stripe_customer_id = Column(String(128), nullable=True)
    stripe_subscription_id = Column(String(128), nullable=True, index=True)
    stripe_price_id = Column(String(128), nullable=True)
    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    current_period_started_at = Column(DateTime, nullable=True)
    current_period_ends_at = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    payment_failed_at = Column(DateTime, nullable=True)
    grace_period_ends_at = Column(DateTime, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisEntitlement(Base):
    __tablename__ = "elfis_entitlements"
    __table_args__ = (
        UniqueConstraint("entitlement_id", name="uq_elfis_entitlement_id"),
        UniqueConstraint(
            "organization_id",
            "feature_code",
            "source",
            name="uq_elfis_entitlement_org_feature_source",
        ),
        CheckConstraint(
            "source IN ('plan','override','trial','promotion','platform_admin')",
            name="ck_elfis_entitlement_source",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    entitlement_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(String(36), nullable=True)
    feature_code = Column(String(64), nullable=False, index=True)
    is_enabled = Column(Boolean, nullable=False)
    source = Column(String(32), nullable=False)
    value = Column(JSON, nullable=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisQuota(Base):
    __tablename__ = "elfis_quotas"
    __table_args__ = (
        UniqueConstraint("quota_id", name="uq_elfis_quota_id"),
        UniqueConstraint(
            "organization_id",
            "quota_code",
            "current_period_started_at",
            name="uq_elfis_quota_org_code_period",
        ),
        CheckConstraint(
            "period IN ('day','month','billing_period','lifetime')",
            name="ck_elfis_quota_period",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    quota_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(String(36), nullable=True)
    quota_code = Column(String(64), nullable=False, index=True)
    limit_value = Column(BigInteger, nullable=True)
    period = Column(String(32), nullable=False)
    hard_limit = Column(Boolean, nullable=False, default=True)
    current_period_started_at = Column(DateTime, nullable=False)
    current_period_ends_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisUsageCounter(Base):
    __tablename__ = "elfis_usage_counters"
    __table_args__ = (
        UniqueConstraint("usage_counter_id", name="uq_elfis_usage_counter_id"),
        UniqueConstraint(
            "organization_id",
            "usage_code",
            "period_started_at",
            name="uq_elfis_usage_org_code_period",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    usage_counter_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(String(36), nullable=True)
    usage_code = Column(String(64), nullable=False, index=True)
    period_started_at = Column(DateTime, nullable=False)
    period_ends_at = Column(DateTime, nullable=False)
    used_value = Column(BigInteger, nullable=False, default=0)
    reserved_value = Column(BigInteger, nullable=False, default=0)
    last_consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisBillingEvent(Base):
    __tablename__ = "elfis_billing_events"
    __table_args__ = (
        UniqueConstraint("billing_event_id", name="uq_elfis_billing_event_id"),
        UniqueConstraint("provider_event_id", name="uq_elfis_billing_provider_event"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    billing_event_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    provider = Column(String(32), nullable=False)
    provider_event_id = Column(String(128), nullable=True, unique=True)
    event_type = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    subscription_id = Column(String(36), nullable=True)
    payload_hash = Column(String(64), nullable=True)
    payload_summary = Column(JSON, nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
