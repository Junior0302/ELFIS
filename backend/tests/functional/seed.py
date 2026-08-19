"""Seed reproductible pour la recette fonctionnelle ELFIS Core."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.billing.billing_types import QuotaCodes, UsageCodes
from app.billing.quota_service import QuotaService
from app.billing.subscription_service import SubscriptionService
from app.models_saas import Organization, OrganizationMember, Subscription, User
from app.services.auth import ensure_rbac_catalog, hash_password
from tests.functional.catalog import ORGS, TEST_PASSWORD, TEST_PASSWORD_HINT, USERS, scenario_matrix


RECETTE_MARKER = "elfis_functional_recette"


def _now() -> datetime:
    return datetime.utcnow()


def assert_safe_environment(*, database_url: str, environment: str) -> None:
    env = (environment or "").strip().lower()
    url = (database_url or "").lower()
    if env in {"production", "prod"}:
        raise RuntimeError("Refus : ELFIS_ENVIRONMENT/APP_ENV=production")
    dangerous = ("prod", "production", "live")
    if any(d in url for d in dangerous) and not any(
        t in url for t in ("test", "functional", "recette", ":memory:", "sqlite")
    ):
        raise RuntimeError(
            f"Refus : DATABASE_URL suspecte pour une base de prod ({database_url!r})"
        )
    if "sqlite" not in url and not any(t in url for t in ("test", "functional", "recette")):
        raise RuntimeError(
            "Refus : nom de base sans 'test', 'functional' ou 'recette' "
            "(sauf SQLite). Utilisez une base dédiée."
        )


def wipe_recette_data(db: Session) -> dict[str, int]:
    """Supprime les données marquées recette (best-effort, ordre FK)."""
    from sqlalchemy import text

    counts: dict[str, int] = {}
    # Approche pragmatique : supprimer users/orgs dont l'email/name contient test.elfis.local / Recette
    emails = [u.email for u in USERS.values()]
    users = db.query(User).filter(User.email.in_(emails)).all()
    user_ids = [u.id for u in users]
    org_names = [o.name for o in ORGS.values()]
    orgs = db.query(Organization).filter(Organization.name.in_(org_names)).all()
    org_ids = [o.id for o in orgs]

    # Tables liées org — best effort
    for table, col in [
        ("elfis_usage_counters", "organization_id"),
        ("elfis_quotas", "organization_id"),
        ("elfis_entitlements", "organization_id"),
        ("elfis_subscriptions", "organization_id"),
        ("subscriptions", "organization_id"),
        ("organization_members", "organization_id"),
        ("ai_agents", "organization_id"),
        ("elfis_security_events", "organization_id"),
        ("elfis_admin_audit_logs", "organization_id"),
        ("elfis_operational_incidents", "organization_id"),
    ]:
        try:
            if org_ids:
                ids = ",".join(str(i) for i in org_ids)
                res = db.execute(text(f"DELETE FROM {table} WHERE {col} IN ({ids})"))
                counts[table] = int(res.rowcount or 0)
        except Exception:
            counts[table] = -1

    if user_ids:
        try:
            ids = ",".join(str(i) for i in user_ids)
            res = db.execute(text(f"DELETE FROM organization_members WHERE user_id IN ({ids})"))
            counts["organization_members_by_user"] = int(res.rowcount or 0)
        except Exception:
            pass
        try:
            ids = ",".join(str(i) for i in user_ids)
            res = db.execute(text(f"DELETE FROM users WHERE id IN ({ids})"))
            counts["users"] = int(res.rowcount or 0)
        except Exception:
            counts["users"] = -1

    if org_ids:
        try:
            ids = ",".join(str(i) for i in org_ids)
            res = db.execute(text(f"DELETE FROM organizations WHERE id IN ({ids})"))
            counts["organizations"] = int(res.rowcount or 0)
        except Exception:
            counts["organizations"] = -1

    db.commit()
    return counts


def _quota_values(profile: str) -> tuple[int | None, int]:
    """Retourne (limit, used) pour documents.processed.month."""
    if profile == "unlimited":
        return None, 0
    if profile == "near_limit":
        return 100, 80
    if profile == "at_limit":
        return 100, 100
    if profile == "over":
        return 100, 110
    return 1000, 5


def _apply_subscription(db: Session, org: Organization, spec) -> Subscription | None:
    now = _now()
    if spec.subscription_status == "none":
        return None

    status = spec.subscription_status
    trial_start = trial_end = None
    period_start = now - timedelta(days=5)
    period_end = now + timedelta(days=25)
    past_due_since = None
    cancel_at_period_end = bool(spec.cancel_at_period_end)
    canceled_at = None
    access_ends_at = None
    grace_note = {}

    if status == "trialing":
        trial_start = now - timedelta(days=2)
        trial_end = now + timedelta(days=12)
        period_start = trial_start
        period_end = trial_end
    elif status == "past_due":
        past_due_since = now - timedelta(days=2 if spec.grace_active else 20)
        period_end = now + timedelta(days=5) if spec.grace_active else now - timedelta(days=1)
        grace_note = {"grace_active": spec.grace_active}
    elif status == "cancelled":
        status = "canceled"  # legacy spelling sometimes
        canceled_at = now - timedelta(days=1)
        period_end = now - timedelta(days=1)
        access_ends_at = period_end
    elif status == "expired":
        period_end = now - timedelta(days=10)
        access_ends_at = period_end
        status = "canceled"

    if cancel_at_period_end and spec.subscription_status != "expired":
        status = "active"
        period_end = now + timedelta(days=10)
        access_ends_at = period_end

    legacy = Subscription(
        organization_id=org.id,
        plan=spec.plan,
        status=status if status != "expired" else "canceled",
        price=19.0,
        stripe_customer_id=f"cus_recette_{org.id}_{uuid4().hex[:8]}",
        stripe_subscription_id=f"sub_recette_{org.id}_{uuid4().hex[:8]}",
        stripe_price_id="price_recette_starter_test",
        trial_start=trial_start,
        trial_end=trial_end,
        trial_used=status != "trialing",
        trial_eligibility_status="already_used" if status != "trialing" else "eligible",
        current_period_start=period_start,
        current_period_end=period_end,
        past_due_since=past_due_since,
        cancel_at_period_end=cancel_at_period_end,
        canceled_at=canceled_at,
        access_ends_at=access_ends_at,
    )
    db.add(legacy)
    db.flush()

    # Sync couche Billing V1
    try:
        SubscriptionService(db).sync_from_legacy(org.id, rebuild=True)
    except Exception:
        pass

    # Quotas de scénario
    limit, used = _quota_values(spec.quota_profile)
    qs = QuotaService(db)
    try:
        qs._ensure_quota(org.id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, now=now)
        check = qs.check(org.id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=0, now=now)
        # Forcer usage
        from app.billing.billing_models import ElfisQuota, ElfisUsageCounter

        quota = (
            db.query(ElfisQuota)
            .filter(
                ElfisQuota.organization_id == org.id,
                ElfisQuota.quota_code == QuotaCodes.DOCUMENTS_PROCESSED_MONTH,
            )
            .first()
        )
        if quota is not None:
            quota.limit_value = limit
            quota.hard_limit = True
        usage = (
            db.query(ElfisUsageCounter)
            .filter(
                ElfisUsageCounter.organization_id == org.id,
                ElfisUsageCounter.usage_code == UsageCodes.DOCUMENTS_PROCESSED,
            )
            .first()
        )
        if usage is None and quota is not None:
            usage = ElfisUsageCounter(
                id=str(uuid4()),
                usage_counter_id=str(uuid4()),
                organization_id=org.id,
                usage_code=UsageCodes.DOCUMENTS_PROCESSED,
                period_started_at=quota.current_period_started_at,
                period_ends_at=quota.current_period_ends_at,
                used_value=used,
                reserved_value=0,
            )
            db.add(usage)
        elif usage is not None:
            usage.used_value = used
    except Exception:
        pass

    org.subscription_plan = spec.plan
    return legacy


def seed_functional_fixtures(db: Session) -> dict[str, Any]:
    """Crée (ou recrée) le jeu de données de recette. Idempotent via wipe préalable."""
    roles = ensure_rbac_catalog(db)
    wiped = wipe_recette_data(db)

    org_rows: dict[str, Organization] = {}
    for key, spec in ORGS.items():
        org = Organization(
            name=spec.name,
            legal_name=spec.legal_name,
            siren=f"900{abs(hash(key)) % 10_000_000:07d}"[:9],
            country="FR",
            currency="EUR",
            subscription_plan=spec.plan,
            platform_status=spec.platform_status,
            platform_suspend_reason="Recette fonctionnelle" if spec.platform_status == "suspended" else "",
            platform_suspended_at=_now() if spec.platform_status == "suspended" else None,
            email=f"{key.lower()}@test.elfis.local",
            city="Paris",
            address="1 rue de la Recette",
            postal_code="75001",
        )
        db.add(org)
        db.flush()
        org_rows[key] = org
        _apply_subscription(db, org, spec)

    user_rows: dict[str, User] = {}
    pwd = hash_password(TEST_PASSWORD)
    for key, spec in USERS.items():
        user = User(
            first_name=spec.first_name,
            last_name=spec.last_name,
            email=spec.email,
            password_hash=pwd,
            firebase_uid="",
            status="active",
            is_platform_admin=spec.is_platform_admin,
        )
        db.add(user)
        db.flush()
        user_rows[key] = user
        if spec.org_key and spec.org_key in org_rows:
            role = roles.get(spec.role) or roles.get("owner")
            db.add(
                OrganizationMember(
                    user_id=user.id,
                    organization_id=org_rows[spec.org_key].id,
                    role_id=role.id,
                    status="active",
                )
            )

    db.commit()

    return {
        "marker": RECETTE_MARKER,
        "wiped": wiped,
        "organizations": {k: {"id": o.id, "name": o.name} for k, o in org_rows.items()},
        "users": {
            k: {
                "id": u.id,
                "email": u.email,
                "org_id": org_rows[USERS[k].org_key].id if USERS[k].org_key in org_rows else None,
                "is_platform_admin": u.is_platform_admin,
            }
            for k, u in user_rows.items()
        },
        "password_hint": TEST_PASSWORD_HINT,
        "password": TEST_PASSWORD,
        "scenarios": scenario_matrix(),
        "note_auth": (
            "POST /api/auth/login est désactivé (Firebase). "
            "Les tests API utilisent create_access_token ; "
            "la recette UI nécessite Firebase Auth test."
        ),
    }
