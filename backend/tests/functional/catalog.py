"""Catalogue des comptes et organisations de recette fonctionnelle.

Tous les identifiants sont fictifs (@test.elfis.local).
Mot de passe unique de recette : voir TEST_PASSWORD (jamais en production).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Mot de passe réservé exclusivement à l'environnement de recette.
TEST_PASSWORD = "ElfisRecette!Test-2026"
TEST_PASSWORD_HINT = "Réservé à ELFIS_ENVIRONMENT=test / functional — jamais production."


@dataclass(frozen=True)
class RecetteUserSpec:
    key: str
    email: str
    first_name: str
    last_name: str
    org_key: str | None
    role: str  # owner|admin|employe|platform
    is_platform_admin: bool = False
    scenario: str = ""


@dataclass(frozen=True)
class RecetteOrgSpec:
    key: str
    name: str
    legal_name: str
    platform_status: str  # active|suspended
    subscription_status: str  # none|trialing|active|past_due|cancelled|expired
    plan: str = "starter"
    cancel_at_period_end: bool = False
    grace_active: bool = True
    quota_profile: str = "normal"  # normal|near_limit|at_limit|over|unlimited
    scenario: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


ORGS: dict[str, RecetteOrgSpec] = {
    "ORG_TRIAL": RecetteOrgSpec(
        key="ORG_TRIAL",
        name="Recette Essai SARL",
        legal_name="Recette Essai SARL",
        platform_status="active",
        subscription_status="trialing",
        quota_profile="normal",
        scenario="Essai gratuit 14 jours en cours",
    ),
    "ORG_ACTIVE": RecetteOrgSpec(
        key="ORG_ACTIVE",
        name="Recette Active SA",
        legal_name="Recette Active SA",
        platform_status="active",
        subscription_status="active",
        quota_profile="normal",
        scenario="Abonnement starter actif 19 €/mois",
    ),
    "ORG_PAST_DUE": RecetteOrgSpec(
        key="ORG_PAST_DUE",
        name="Recette Impayé SAS",
        legal_name="Recette Impayé SAS",
        platform_status="active",
        subscription_status="past_due",
        grace_active=True,
        quota_profile="normal",
        scenario="Past due avec période de grâce active",
    ),
    "ORG_PAST_DUE_EXPIRED": RecetteOrgSpec(
        key="ORG_PAST_DUE_EXPIRED",
        name="Recette Grâce Expirée",
        legal_name="Recette Grâce Expirée",
        platform_status="active",
        subscription_status="past_due",
        grace_active=False,
        quota_profile="normal",
        scenario="Past due — grâce dépassée",
    ),
    "ORG_CANCELLED": RecetteOrgSpec(
        key="ORG_CANCELLED",
        name="Recette Résilié SCI",
        legal_name="Recette Résilié SCI",
        platform_status="active",
        subscription_status="active",
        cancel_at_period_end=True,
        quota_profile="normal",
        scenario="Annulation en fin de période (droits jusqu'à échéance)",
    ),
    "ORG_EXPIRED": RecetteOrgSpec(
        key="ORG_EXPIRED",
        name="Recette Expiré EURL",
        legal_name="Recette Expiré EURL",
        platform_status="active",
        subscription_status="expired",
        quota_profile="normal",
        scenario="Abonnement terminé — consultation seule",
    ),
    "ORG_SUSPENDED": RecetteOrgSpec(
        key="ORG_SUSPENDED",
        name="Recette Suspendue",
        legal_name="Recette Suspendue",
        platform_status="suspended",
        subscription_status="active",
        quota_profile="normal",
        scenario="Organisation suspendue par la plateforme",
    ),
    "ORG_SECOND_TENANT": RecetteOrgSpec(
        key="ORG_SECOND_TENANT",
        name="Recette Autre Tenant",
        legal_name="Recette Autre Tenant",
        platform_status="active",
        subscription_status="active",
        quota_profile="normal",
        scenario="Isolation multi-tenant",
    ),
    "ORG_QUOTA_NEAR": RecetteOrgSpec(
        key="ORG_QUOTA_NEAR",
        name="Recette Quota 80%",
        legal_name="Recette Quota 80%",
        platform_status="active",
        subscription_status="active",
        quota_profile="near_limit",
        scenario="Quota documents ~80%",
    ),
    "ORG_QUOTA_FULL": RecetteOrgSpec(
        key="ORG_QUOTA_FULL",
        name="Recette Quota Plein",
        legal_name="Recette Quota Plein",
        platform_status="active",
        subscription_status="active",
        quota_profile="at_limit",
        scenario="Quota documents atteint",
    ),
    "ORG_NONE": RecetteOrgSpec(
        key="ORG_NONE",
        name="Recette Sans Abo",
        legal_name="Recette Sans Abo",
        platform_status="active",
        subscription_status="none",
        quota_profile="normal",
        scenario="Organisation sans abonnement",
    ),
}


USERS: dict[str, RecetteUserSpec] = {
    "platform_admin": RecetteUserSpec(
        key="platform_admin",
        email="platform.admin@test.elfis.local",
        first_name="Platform",
        last_name="Admin",
        org_key="ORG_ACTIVE",
        role="owner",
        is_platform_admin=True,
        scenario="ELFIS Admin plateforme",
    ),
    "org_admin": RecetteUserSpec(
        key="org_admin",
        email="org.admin@test.elfis.local",
        first_name="Org",
        last_name="Admin",
        org_key="ORG_ACTIVE",
        role="owner",
        scenario="Admin organisation active",
    ),
    "member": RecetteUserSpec(
        key="member",
        email="member@test.elfis.local",
        first_name="Simple",
        last_name="Membre",
        org_key="ORG_ACTIVE",
        role="employe",
        scenario="Membre permissions limitées",
    ),
    "trial": RecetteUserSpec(
        key="trial",
        email="trial@test.elfis.local",
        first_name="Essai",
        last_name="User",
        org_key="ORG_TRIAL",
        role="owner",
        scenario="Essai gratuit",
    ),
    "active": RecetteUserSpec(
        key="active",
        email="active@test.elfis.local",
        first_name="Actif",
        last_name="User",
        org_key="ORG_ACTIVE",
        role="admin",
        scenario="Abonnement actif",
    ),
    "pastdue": RecetteUserSpec(
        key="pastdue",
        email="pastdue@test.elfis.local",
        first_name="Past",
        last_name="Due",
        org_key="ORG_PAST_DUE",
        role="owner",
        scenario="Past due grâce active",
    ),
    "cancelled": RecetteUserSpec(
        key="cancelled",
        email="cancelled@test.elfis.local",
        first_name="Cancel",
        last_name="User",
        org_key="ORG_CANCELLED",
        role="owner",
        scenario="Annulation fin de période",
    ),
    "suspended": RecetteUserSpec(
        key="suspended",
        email="suspended@test.elfis.local",
        first_name="Suspend",
        last_name="User",
        org_key="ORG_SUSPENDED",
        role="owner",
        scenario="Org suspendue",
    ),
    "other_tenant": RecetteUserSpec(
        key="other_tenant",
        email="other.tenant@test.elfis.local",
        first_name="Autre",
        last_name="Tenant",
        org_key="ORG_SECOND_TENANT",
        role="owner",
        scenario="Deuxième tenant",
    ),
    "no_sub": RecetteUserSpec(
        key="no_sub",
        email="nosub@test.elfis.local",
        first_name="Sans",
        last_name="Abo",
        org_key="ORG_NONE",
        role="owner",
        scenario="Sans abonnement",
    ),
    "quota_near": RecetteUserSpec(
        key="quota_near",
        email="quota.near@test.elfis.local",
        first_name="Quota",
        last_name="Near",
        org_key="ORG_QUOTA_NEAR",
        role="owner",
        scenario="Quota ~80%",
    ),
    "quota_full": RecetteUserSpec(
        key="quota_full",
        email="quota.full@test.elfis.local",
        first_name="Quota",
        last_name="Full",
        org_key="ORG_QUOTA_FULL",
        role="owner",
        scenario="Quota atteint",
    ),
    "past_due_expired": RecetteUserSpec(
        key="past_due_expired",
        email="pastdue.expired@test.elfis.local",
        first_name="Grace",
        last_name="Expired",
        org_key="ORG_PAST_DUE_EXPIRED",
        role="owner",
        scenario="Past due hors grâce",
    ),
    "expired": RecetteUserSpec(
        key="expired",
        email="expired@test.elfis.local",
        first_name="Expire",
        last_name="User",
        org_key="ORG_EXPIRED",
        role="owner",
        scenario="Abonnement expiré",
    ),
}


def scenario_matrix() -> list[dict[str, str]]:
    rows = []
    for u in USERS.values():
        org = ORGS.get(u.org_key) if u.org_key else None
        rows.append(
            {
                "user_key": u.key,
                "email": u.email,
                "org_key": u.org_key or "",
                "subscription": org.subscription_status if org else "",
                "platform_status": org.platform_status if org else "",
                "quota_profile": org.quota_profile if org else "",
                "scenario": u.scenario,
            }
        )
    return rows
