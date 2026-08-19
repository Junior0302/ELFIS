"""Service Command Center — agrégation déterministe (pas de calcul FE)."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.accounting.accounting_service import AccountingService
from app.dashboard_command_center.schemas import (
    CommandAiInsightsOut,
    CommandCenterOut,
    CommandHealthServiceOut,
    CommandPriorityOut,
    CommandSmartSummaryOut,
    CommandSummaryMetricOut,
    CommandSystemHealthOut,
)
from app.dashboard_launch.service import LaunchDashboardService
from app.work_queue.service import WorkQueueService
from app.financial.engine import FinancialEngine
from app.models_saas import Customer, Organization, SalesDocument, User
from app.models_vault import VaultDocument
from app.notifications.notification_service import NotificationService
from app.subscriptions.access import get_subscription_access

MAX_PRIORITIES = 5
MAX_TIMELINE = 20
MAX_DECISION_INSIGHTS = 3


class CommandCenterService:
    def __init__(self, db: Session):
        self.db = db
        self.launch = LaunchDashboardService(db)

    def build(
        self,
        *,
        organization_id: int,
        user: User,
        permissions: list[str],
    ) -> CommandCenterOut:
        org = self.db.get(Organization, organization_id)
        if org is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "ORGANIZATION_NOT_FOUND", "message": "Organisation introuvable."},
            )

        access = get_subscription_access(self.db, organization_id, user=user)
        snap = self._safe_financial_snapshot(organization_id, access.has_access)
        priorities = self._priorities(
            organization_id=organization_id,
            user_id=user.id,
            permissions=permissions,
            access=access,
            snap=snap,
        )
        summary = self._smart_summary(
            organization_id=organization_id,
            permissions=permissions,
            snap=snap,
            access_granted=access.has_access,
        )
        timeline = self.launch.recent_activity(
            organization_id, permissions, limit=MAX_TIMELINE
        )
        quick = self.launch.quick_actions(permissions)
        health = self._system_health(
            organization_id=organization_id,
            user_id=user.id,
            access=access,
        )
        summary_wq = WorkQueueService(self.db).summary_for_command_center(
            organization_id=organization_id,
            permissions=permissions,
            limit=MAX_DECISION_INSIGHTS,
        )
        insights = summary_wq.todo_insights
        counts = summary_wq.counts.model_dump()
        count_msg = (
            f"{counts['todo']} à traiter · {counts['in_progress']} en cours · {counts['waiting']} en attente"
        )
        ai_insights = (
            CommandAiInsightsOut(
                status="ready",
                title="À examiner",
                message=count_msg,
                insights=insights,
                work_queue_path="/work-queue",
                counts=counts,
            )
            if insights
            else CommandAiInsightsOut(
                status="empty",
                title="À examiner",
                message="Aucune décision ne nécessite votre attention actuellement.",
                insights=[],
                work_queue_path="/work-queue",
                counts=counts,
            )
        )

        return CommandCenterOut(
            organization_name=org.name or "",
            priorities=priorities[:MAX_PRIORITIES],
            smart_summary=summary,
            activity_timeline=timeline,
            ai_insights=ai_insights,
            quick_actions=quick,
            system_health=health,
            generated_at=datetime.utcnow(),
        )

    def _safe_financial_snapshot(self, organization_id: int, entitled: bool) -> dict | None:
        if not entitled:
            return None
        try:
            return FinancialEngine(self.db).snapshot(organization_id)
        except Exception:
            return None

    def _priorities(
        self,
        *,
        organization_id: int,
        user_id: int,
        permissions: list[str],
        access,
        snap: dict | None,
    ) -> list[CommandPriorityOut]:
        items: list[CommandPriorityOut] = []

        if not access.has_access:
            items.append(
                CommandPriorityOut(
                    id="subscription-required",
                    severity="critical",
                    title="Abonnement requis",
                    description="Activez ou réactivez votre abonnement pour retrouver l’accès complet.",
                    action_path="/abonnement",
                    permission="subscription.manage",
                )
            )
        elif access.read_only:
            items.append(
                CommandPriorityOut(
                    id="subscription-readonly",
                    severity="high",
                    title="Accès en lecture seule",
                    description="Un problème de paiement limite temporairement les actions d’écriture.",
                    action_path="/abonnement",
                    permission="subscription.manage",
                )
            )

        if snap and self._allows(permissions, "invoice.read"):
            overdue = int(snap.get("overdue_count") or 0)
            if overdue > 0:
                items.append(
                    CommandPriorityOut(
                        id="invoices-overdue",
                        severity="critical" if float(snap.get("overdue_amount") or 0) > 10000 else "high",
                        title=f"{overdue} facture(s) en retard",
                        description=(
                            f"{float(snap.get('overdue_amount') or 0):.2f} € à relancer auprès de vos clients."
                        ),
                        action_path="/facturation",
                        permission="invoice.read",
                    )
                )
            unpaid = int(snap.get("pending_count") or 0)
            if unpaid > 0 and overdue == 0:
                items.append(
                    CommandPriorityOut(
                        id="invoices-unpaid",
                        severity="medium",
                        title=f"{unpaid} facture(s) en attente",
                        description="Suivez les encaissements et relances depuis la facturation.",
                        action_path="/facturation",
                        permission="invoice.read",
                    )
                )
            docs = int(snap.get("documents_to_process") or 0)
            if docs > 0 and self._allows(permissions, "documents.read"):
                items.append(
                    CommandPriorityOut(
                        id="documents-to-process",
                        severity="medium",
                        title=f"{docs} document(s) à traiter",
                        description="Des documents fournisseurs attendent une suite dans votre espace.",
                        action_path="/documents",
                        permission="documents.read",
                    )
                )

        # Les propositions comptables sont exposées via Decision Center (« À examiner »)
        # pour éviter le doublon visuel avec Priority Center.

        unread = self._safe_unread(organization_id, user_id)
        if unread and unread > 0:
            items.append(
                CommandPriorityOut(
                    id="notifications-unread",
                    severity="low",
                    title=f"{unread} notification(s) non lue(s)",
                    description="Consultez le centre de notifications pour les dernières alertes.",
                    action_path="/notifications",
                    permission="",
                )
            )

        # Filtrer les priorités dont l'utilisateur n'a pas la permission d'agir
        filtered: list[CommandPriorityOut] = []
        for p in items:
            if p.permission and not self._allows(permissions, p.permission):
                # Garder si permission vide ou subscription.manage souvent owner-only —
                # si pas de droit, on saute sauf notifications.
                if p.permission == "subscription.manage" and not self._allows(permissions, "subscription.manage"):
                    if "*" not in permissions and "subscription.manage" not in permissions:
                        continue
                else:
                    continue
            filtered.append(p)
        return filtered

    def _smart_summary(
        self,
        *,
        organization_id: int,
        permissions: list[str],
        snap: dict | None,
        access_granted: bool,
    ) -> CommandSmartSummaryOut:
        metrics: list[CommandSummaryMetricOut] = []

        if self._allows(permissions, "invoice.read"):
            customers = (
                self.db.query(func.count(Customer.id))
                .filter(Customer.organization_id == organization_id)
                .scalar()
                or 0
            )
            invoices = (
                self.db.query(func.count(SalesDocument.id))
                .filter(
                    SalesDocument.organization_id == organization_id,
                    SalesDocument.doc_type == "facture",
                    SalesDocument.status != "cancelled",
                )
                .scalar()
                or 0
            )
            metrics.append(
                CommandSummaryMetricOut(
                    key="customers",
                    label="Clients",
                    value=int(customers),
                    path="/clients",
                )
            )
            metrics.append(
                CommandSummaryMetricOut(
                    key="invoices",
                    label="Factures",
                    value=int(invoices),
                    path="/facturation",
                )
            )

        if self._allows(permissions, "documents.read") or self._allows(permissions, "documents.write"):
            docs = (
                self.db.query(func.count(VaultDocument.id))
                .filter(VaultDocument.organization_id == organization_id)
                .scalar()
                or 0
            )
            metrics.append(
                CommandSummaryMetricOut(
                    key="documents",
                    label="Documents",
                    value=int(docs),
                    path="/documents",
                )
            )

        if snap and access_granted:
            if snap.get("overdue_count") is not None:
                metrics.append(
                    CommandSummaryMetricOut(
                        key="overdue",
                        label="Factures en retard",
                        value=int(snap["overdue_count"]),
                        path="/facturation",
                    )
                )
            if snap.get("unpaid_amount") is not None:
                metrics.append(
                    CommandSummaryMetricOut(
                        key="unpaid_amount",
                        label="Montant dû",
                        value=float(snap["unpaid_amount"]),
                        unit="EUR",
                        path="/facturation",
                    )
                )

        if not metrics:
            headline = "Aucune donnée métier accessible pour le moment."
        elif snap and snap.get("has_data"):
            headline = "Voici l’état actuel de votre activité."
        else:
            headline = "Voici un aperçu de votre espace ComptaPilot."

        return CommandSmartSummaryOut(
            headline=headline,
            metrics=metrics,
            has_financial_data=bool(snap and snap.get("has_data")),
        )

    def _system_health(
        self,
        *,
        organization_id: int,
        user_id: int,
        access,
    ) -> CommandSystemHealthOut:
        services: list[CommandHealthServiceOut] = []

        # Billing — état réellement connu via moteur d'accès
        if not access.has_access:
            billing_status = "critical"
            billing_detail = "Accès abonnement indisponible."
        elif access.read_only:
            billing_status = "warning"
            billing_detail = "Période de grâce — écriture limitée."
        else:
            billing_status = "ok"
            billing_detail = "Abonnement actif."
        services.append(
            CommandHealthServiceOut(
                key="billing",
                label="Facturation / abonnement",
                status=billing_status,
                detail=billing_detail,
            )
        )

        # Vault — connu seulement si la requête count réussit
        try:
            self.db.query(func.count(VaultDocument.id)).filter(
                VaultDocument.organization_id == organization_id
            ).scalar()
            services.append(
                CommandHealthServiceOut(
                    key="vault",
                    label="Vault",
                    status="ok",
                    detail="Espace documentaire accessible.",
                )
            )
        except Exception:
            services.append(
                CommandHealthServiceOut(
                    key="vault",
                    label="Vault",
                    status="degraded",
                    detail="Impossible de vérifier le coffre documentaire.",
                )
            )

        # Notifications — connu si unread_count répond
        try:
            NotificationService(self.db).get_unread_count(
                organization_id=organization_id, user_id=user_id
            )
            services.append(
                CommandHealthServiceOut(
                    key="notifications",
                    label="Notifications",
                    status="ok",
                    detail="Service de notifications accessible.",
                )
            )
        except Exception:
            services.append(
                CommandHealthServiceOut(
                    key="notifications",
                    label="Notifications",
                    status="degraded",
                    detail="Impossible de vérifier les notifications.",
                )
            )

        # Search / Document Intelligence : non exposés en OK (état org inconnu en V1)
        return CommandSystemHealthOut(services=services)

    def _accounting_review_count(self, organization_id: int) -> int:
        try:
            _, total = AccountingService(self.db).list_proposals(
                organization_id=organization_id,
                requires_review=True,
                page=1,
                page_size=1,
            )
            return int(total or 0)
        except Exception:
            return 0

    def _safe_unread(self, organization_id: int, user_id: int) -> int | None:
        try:
            return int(
                NotificationService(self.db).get_unread_count(
                    organization_id=organization_id, user_id=user_id
                )
            )
        except Exception:
            return None

    @staticmethod
    def _allows(permissions: list[str], permission: str) -> bool:
        if not permission:
            return True
        if "*" in permissions:
            return True
        if permission in permissions:
            return True
        if permission == "documents.write" and (
            "documents.write" in permissions
            or "documents.create" in permissions
            or "documents.*" in permissions
        ):
            return True
        if permission == "ai.analysis" and (
            "ai.analysis" in permissions or "accounting.view" in permissions
        ):
            return True
        if permission == "documents.read" and (
            "documents.read" in permissions or "documents.*" in permissions
        ):
            return True
        return False
