"""Service Launch Dashboard — checklist + activité (EXISTS, pas de N+1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from app.models_saas import Contact, Customer, Organization, OrganizationMember, SalesDocument, User
from app.models_vault import VaultDocument
from app.dashboard_launch.schemas import (
    LaunchActivityItemOut,
    LaunchDashboardOut,
    LaunchOnboardingOut,
    LaunchOrganizationOut,
    LaunchQuickActionOut,
    LaunchRecommendedActionOut,
    LaunchStepOut,
    LaunchUserOut,
)

DEMO_INVOICE_FILENAMES = frozenset(
    {
        "demo_facture_orange.pdf",
        "4205f6c2e41a_demo_facture_orange.pdf",
    }
)

STEP_META: dict[str, dict[str, str]] = {
    "company_setup": {
        "label": "Configurer votre entreprise",
        "title": "Finalisez la configuration de votre entreprise",
        "description": "Complétez les informations essentielles pour préparer votre espace.",
        "action_label": "Continuer la configuration",
        "action_path": "/onboarding/entreprise",
        "perm": "",
    },
    "first_customer": {
        "label": "Ajouter votre premier client",
        "title": "Ajoutez votre premier client",
        "description": "Créez une fiche client pour préparer vos premiers devis et factures.",
        "action_label": "Ajouter un client",
        "action_path": "/clients",
        "perm": "invoice.create",
    },
    "first_supplier": {
        "label": "Ajouter votre premier fournisseur",
        "title": "Ajoutez votre premier fournisseur",
        "description": "Centralisez les coordonnées de vos fournisseurs et préparez le suivi de vos achats.",
        "action_label": "Ajouter un fournisseur",
        "action_path": "/fournisseurs",
        "perm": "invoice.create",
    },
    "first_invoice": {
        "label": "Créer votre première facture",
        "title": "Créez votre première facture",
        "description": "Commencez à facturer depuis ComptaPilot et centralisez automatiquement votre document.",
        "action_label": "Créer une facture",
        "action_path": "/facturation",
        "perm": "invoice.create",
    },
    "first_document": {
        "label": "Importer votre premier document",
        "title": "Importez votre premier document",
        "description": "Ajoutez une facture ou un justificatif pour démarrer votre organisation documentaire.",
        "action_label": "Importer un document",
        "action_path": "/documents",
        "perm": "documents.write",
    },
    "accounting_discovery": {
        "label": "Découvrir votre espace comptable",
        "title": "Découvrez votre espace comptable",
        "description": "Consultez les propositions, écritures et outils de suivi disponibles.",
        "action_label": "Ouvrir l’espace comptable",
        "action_path": "/accounting",
        "perm": "ai.analysis",
    },
}

STEP_ORDER = (
    "company_setup",
    "first_customer",
    "first_supplier",
    "first_invoice",
    "first_document",
    "accounting_discovery",
)


@dataclass(frozen=True)
class _Perms:
    raw: list[str]

    def allows(self, permission: str) -> bool:
        if not permission:
            return True
        if "*" in self.raw:
            return True
        if permission in self.raw:
            return True
        # documents.write souvent couvert par documents.create
        if permission == "documents.write" and (
            "documents.write" in self.raw or "documents.create" in self.raw or "documents.*" in self.raw
        ):
            return True
        if permission == "ai.analysis" and (
            "ai.analysis" in self.raw or "accounting.view" in self.raw
        ):
            return True
        return False


class LaunchDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def build(
        self,
        *,
        organization_id: int,
        user: User,
        permissions: list[str],
    ) -> LaunchDashboardOut:
        org = self.db.get(Organization, organization_id)
        if org is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "ORGANIZATION_NOT_FOUND", "message": "Organisation introuvable."},
            )

        perms = _Perms(permissions)
        completed_map = self._completed_map(org, organization_id, user.id)
        steps = self._build_steps(completed_map, perms)
        completed_steps = sum(1 for s in steps if s.completed)
        total_steps = len(steps)
        progress = round(completed_steps / total_steps * 100) if total_steps else 0
        recommended = self._recommended(completed_map, perms)
        quick = self._quick_actions(perms)
        activity = self._recent_activity(organization_id, perms, limit=5)

        display = (user.first_name or "").strip() or None
        return LaunchDashboardOut(
            workspace_ready=bool(getattr(org, "setup_completed", False)),
            user=LaunchUserOut(display_name=display),
            organization=LaunchOrganizationOut(name=org.name or ""),
            onboarding=LaunchOnboardingOut(
                completed_steps=completed_steps,
                total_steps=total_steps,
                progress=progress,
                steps=steps,
                recommended_action=recommended,
                all_completed=completed_steps == total_steps,
            ),
            quick_actions=quick,
            recent_activity=activity,
        )

    def mark_accounting_discovered(self, *, organization_id: int, user_id: int) -> bool:
        member = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
            )
            .one_or_none()
        )
        if member is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "MEMBERSHIP_NOT_FOUND", "message": "Adhésion introuvable."},
            )
        if getattr(member, "accounting_hub_visited_at", None) is None:
            member.accounting_hub_visited_at = datetime.utcnow()
            self.db.add(member)
            self.db.commit()
        return True

    def quick_actions(self, permissions: list[str]) -> list[LaunchQuickActionOut]:
        """API publique réutilisée par le Command Center (pas de duplication)."""
        return self._quick_actions(_Perms(permissions))

    def recent_activity(
        self,
        organization_id: int,
        permissions: list[str],
        *,
        limit: int = 5,
    ) -> list[LaunchActivityItemOut]:
        """API publique réutilisée par le Command Center."""
        return self._recent_activity(organization_id, _Perms(permissions), limit=limit)

    def _completed_map(self, org: Organization, organization_id: int, user_id: int) -> dict[str, bool]:
        company = bool(getattr(org, "setup_completed", False))
        has_customer = self.db.query(
            exists().where(Customer.organization_id == organization_id)
        ).scalar()
        has_supplier = self.db.query(
            exists().where(
                and_(
                    Contact.organization_id == organization_id,
                    Contact.contact_type.in_(("supplier", "customer_and_supplier")),
                    Contact.status == "active",
                )
            )
        ).scalar()
        has_invoice = self.db.query(
            exists().where(
                and_(
                    SalesDocument.organization_id == organization_id,
                    SalesDocument.doc_type == "facture",
                    SalesDocument.status != "cancelled",
                )
            )
        ).scalar()
        has_document = self.db.query(
            exists().where(VaultDocument.organization_id == organization_id)
        ).scalar()

        member = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
            .one_or_none()
        )
        accounting = bool(member and getattr(member, "accounting_hub_visited_at", None))

        return {
            "company_setup": company,
            "first_customer": bool(has_customer),
            "first_supplier": bool(has_supplier),
            "first_invoice": bool(has_invoice),
            "first_document": bool(has_document),
            "accounting_discovery": accounting,
        }

    def _build_steps(self, completed_map: dict[str, bool], perms: _Perms) -> list[LaunchStepOut]:
        out: list[LaunchStepOut] = []
        for key in STEP_ORDER:
            meta = STEP_META[key]
            path = meta["action_path"] or None
            label_action = meta["action_label"] if path else None
            # Pas de CTA si pas de route ou permission insuffisante
            if path and meta["perm"] and not perms.allows(meta["perm"]):
                path = None
                label_action = None
            if not path:
                label_action = None
            out.append(
                LaunchStepOut(
                    key=key,
                    label=meta["label"],
                    completed=bool(completed_map.get(key)),
                    action_path=path if not completed_map.get(key) else None,
                    action_label=label_action if not completed_map.get(key) else None,
                )
            )
        return out

    def _recommended(
        self, completed_map: dict[str, bool], perms: _Perms
    ) -> LaunchRecommendedActionOut | None:
        for key in STEP_ORDER:
            if completed_map.get(key):
                continue
            meta = STEP_META[key]
            path = meta["action_path"]
            if not path:
                continue
            if meta["perm"] and not perms.allows(meta["perm"]):
                continue
            return LaunchRecommendedActionOut(
                key=key,
                title=meta["title"],
                description=meta["description"],
                action_label=meta["action_label"],
                action_path=path,
            )
        return None

    def _quick_actions(self, perms: _Perms) -> list[LaunchQuickActionOut]:
        candidates = [
            ("new_customer", "Nouveau client", "Créer une fiche client", "/clients", "invoice.create"),
            ("new_invoice", "Nouvelle facture", "Émettre une facture", "/facturation", "invoice.create"),
            (
                "import_document",
                "Importer un document",
                "Ajouter un justificatif au coffre",
                "/documents",
                "documents.write",
            ),
            (
                "open_accounting",
                "Espace comptable",
                "Découvrir les outils comptables",
                "/accounting",
                "ai.analysis",
            ),
        ]
        # Max 4 — fournisseur exclu (pas de route FE)
        actions: list[LaunchQuickActionOut] = []
        for key, label, desc, path, perm in candidates:
            if not perms.allows(perm):
                continue
            actions.append(
                LaunchQuickActionOut(
                    key=key,
                    label=label,
                    description=desc,
                    path=path,
                    enabled=True,
                )
            )
            if len(actions) >= 4:
                break
        return actions

    def _recent_activity(
        self, organization_id: int, perms: _Perms, *, limit: int = 5
    ) -> list[LaunchActivityItemOut]:
        items: list[LaunchActivityItemOut] = []
        per_source = max(limit, 5)

        if perms.allows("invoice.read"):
            customers = (
                self.db.query(Customer)
                .filter(Customer.organization_id == organization_id)
                .order_by(Customer.created_at.desc())
                .limit(per_source)
                .all()
            )
            for row in customers:
                items.append(
                    LaunchActivityItemOut(
                        id=f"customer-{row.id}",
                        type="customer_created",
                        title="Client ajouté",
                        description=row.name or "Nouveau client",
                        occurred_at=row.created_at or datetime.utcnow(),
                        path="/clients",
                    )
                )
            invoices = (
                self.db.query(SalesDocument)
                .filter(
                    SalesDocument.organization_id == organization_id,
                    SalesDocument.doc_type == "facture",
                    SalesDocument.status != "cancelled",
                )
                .order_by(SalesDocument.created_at.desc())
                .limit(per_source)
                .all()
            )
            for row in invoices:
                items.append(
                    LaunchActivityItemOut(
                        id=f"invoice-{row.id}",
                        type="invoice_created",
                        title="Facture créée",
                        description=row.number or row.customer_name or "Facture",
                        occurred_at=row.created_at or datetime.utcnow(),
                        path="/facturation",
                    )
                )

        if perms.allows("documents.read") or perms.allows("documents.write"):
            docs = (
                self.db.query(VaultDocument)
                .filter(VaultDocument.organization_id == organization_id)
                .order_by(VaultDocument.created_at.desc())
                .limit(per_source)
                .all()
            )
            for row in docs:
                items.append(
                    LaunchActivityItemOut(
                        id=f"document-{row.id}",
                        type="document_imported",
                        title="Document importé",
                        description=row.original_filename or "Document",
                        occurred_at=row.created_at or datetime.utcnow(),
                        path="/documents",
                    )
                )

        items.sort(key=lambda x: x.occurred_at, reverse=True)
        return items[: max(1, min(limit, 20))]
