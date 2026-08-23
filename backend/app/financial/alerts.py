"""Moteur d'alertes financières normalisées.

Chaque alerte est produite au format ``FinancialAlert`` (code stable, sévérité,
titre, message, action recommandée). Les règles sont des fonctions pures du
snapshot du Financial Engine — aucune requête SQL ici.

Seuils configurables via app.config :
- financial_treasury_low_threshold  (défaut 5 000 €)
- financial_treasury_critical_threshold (défaut 1 000 €)
- financial_vat_high_threshold      (défaut 5 000 €)
"""

from __future__ import annotations

from app.config import settings
from app.financial.financial_types import AlertSeverity, FinancialAlert


def _threshold(name: str, default: float) -> float:
    return float(getattr(settings, name, default))


def build_alerts(snap: dict) -> list[FinancialAlert]:
    alerts: list[FinancialAlert] = []
    org = snap["organization_id"]

    # 1. Trésorerie faible / critique
    low = _threshold("financial_treasury_low_threshold", 5000.0)
    critical = _threshold("financial_treasury_critical_threshold", 1000.0)
    treasury_value = snap.get("treasury")
    if (
        snap["has_bank"]
        and snap.get("treasury_homogeneous", True)
        and treasury_value is not None
    ):
        if treasury_value < critical:
            alerts.append(
                FinancialAlert(
                    id=f"{org}-treasury_critical",
                    code="TREASURY_CRITICAL",
                    severity=AlertSeverity.critical,
                    title="Trésorerie critique",
                    message=f"Solde bancaire de {treasury_value:.2f} €, sous le seuil critique de {critical:.0f} €.",
                    action="Relancer les impayés et reporter toute dépense non essentielle.",
                    value=treasury_value,
                )
            )
        elif treasury_value < low:
            alerts.append(
                FinancialAlert(
                    id=f"{org}-treasury_low",
                    code="TREASURY_LOW",
                    severity=AlertSeverity.warning,
                    title="Trésorerie faible",
                    message=f"Solde bancaire de {treasury_value:.2f} €, sous le seuil de vigilance de {low:.0f} €.",
                    action="Surveiller les décaissements et accélérer les encaissements.",
                    value=treasury_value,
                )
            )

    # 2. TVA importante à provisionner
    vat_high = _threshold("financial_vat_high_threshold", 5000.0)
    if snap["vat_estimated"] > vat_high:
        alerts.append(
            FinancialAlert(
                id=f"{org}-vat_high",
                code="VAT_HIGH",
                severity=AlertSeverity.warning,
                title="TVA importante à provisionner",
                message=f"TVA estimée à {snap['vat_estimated']:.2f} € (collectée − déductible).",
                action="Provisionner le montant avant la prochaine échéance de TVA.",
                value=snap["vat_estimated"],
            )
        )

    # 3. Factures impayées
    if snap["overdue_count"]:
        severity = (
            AlertSeverity.critical if snap["overdue_amount"] > 10000 else AlertSeverity.warning
        )
        alerts.append(
            FinancialAlert(
                id=f"{org}-invoices_overdue",
                code="INVOICE_OVERDUE",
                severity=severity,
                title="Factures clients impayées",
                message=(
                    f"{snap['overdue_count']} facture(s) en retard pour {snap['overdue_amount']:.2f} €."
                ),
                action="Relancer les clients concernés (relance automatique disponible).",
                value=snap["overdue_amount"],
            )
        )

    # 4. Dépenses inhabituelles (anomalies bancaires)
    if snap["anomalies"]:
        alerts.append(
            FinancialAlert(
                id=f"{org}-unusual_expense",
                code="UNUSUAL_EXPENSE",
                severity=AlertSeverity.info,
                title="Opérations inhabituelles détectées",
                message=(
                    f"{snap['anomalies']} opération(s) bancaire(s) signalée(s) "
                    f"(montant inhabituel ou doublon)."
                ),
                action="Vérifier les opérations signalées dans le module Banque.",
                value=float(snap["anomalies"]),
            )
        )

    # 5. Synchronisation bancaire absente ou en erreur
    sync = snap["sync"]
    if sync["status"] == "error":
        alerts.append(
            FinancialAlert(
                id=f"{org}-sync_error",
                code="SYNC_ERROR",
                severity=AlertSeverity.critical,
                title="Connexion bancaire en erreur",
                message=f"{sync['errors']} connexion(s) bancaire(s) en erreur.",
                action="Reconnecter la banque depuis le module Banque.",
                value=float(sync["errors"]),
            )
        )
    elif sync["status"] == "stale":
        alerts.append(
            FinancialAlert(
                id=f"{org}-sync_missing",
                code="SYNC_MISSING",
                severity=AlertSeverity.warning,
                title="Synchronisation bancaire absente",
                message="Aucune synchronisation bancaire depuis plus de 7 jours.",
                action="Lancer une synchronisation pour actualiser les indicateurs.",
            )
        )
    elif sync["status"] == "none" and snap["has_data"]:
        alerts.append(
            FinancialAlert(
                id=f"{org}-sync_none",
                code="SYNC_NOT_CONFIGURED",
                severity=AlertSeverity.info,
                title="Aucune banque connectée",
                message="Connectez votre banque pour fiabiliser la trésorerie et les alertes.",
                action="Connecter une banque dans le module Banque.",
            )
        )

    # 6. Documents à traiter
    if snap["documents_to_process"]:
        alerts.append(
            FinancialAlert(
                id=f"{org}-docs_pending",
                code="DOCUMENTS_PENDING",
                severity=AlertSeverity.info,
                title="Documents à traiter",
                message=f"{snap['documents_to_process']} document(s) fournisseur en attente de traitement.",
                action="Vérifier les documents dans le module Factures.",
                value=float(snap["documents_to_process"]),
            )
        )

    order = {AlertSeverity.critical: 0, AlertSeverity.warning: 1, AlertSeverity.info: 2}
    alerts.sort(key=lambda a: order[a.severity])
    return alerts
