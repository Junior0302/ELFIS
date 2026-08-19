"""Deterministic insight rules — consume existing SalesPilot scores, no AI."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.sales_crm.models import (
    SalesActivity,
    SalesOpportunity,
    SalesPipelineStage,
    SalesTask,
)
from app.sales_crm.pipeline_service import days_in_stage, health_score_for, risk_level_for
from app.sales_crm.service import soft_alive
from app.sales_intelligence.actions import action, standard_actions
from app.sales_intelligence.enums import (
    ACTIONABLE_DECISION_TYPES,
    NOTIFIABLE_TYPES,
    InsightCategory,
    InsightSeverity,
    InsightType,
)
from app.sales_intelligence.explanations import evidence_item, explanation
from app.sales_intelligence.priorities import (
    CLOSING_SOON_DAYS,
    CONGESTED_STAGE_COUNT,
    HIGH_RISK_SHARE,
    HIGH_VALUE_AMOUNT,
    INACTIVE_DAYS,
    LOW_HEALTH,
    MANY_WITHOUT_NEXT_ACTION,
    MEETING_IMMINENT_HOURS,
    NEGOTIATION_LONG_DAYS,
    PROPOSAL_EXPIRING_DAYS,
    STAGE_AGING_CRITICAL_DAYS,
    STAGE_AGING_DAYS,
    priority_score,
    severity_for_inactive_high_value,
)
from app.sales_intelligence.signals import InsightDraft
from app.sales_proposals.enums import ProposalStatus
from app.sales_proposals.models import CommercialProposal, CommercialProposalVersion


def _now() -> datetime:
    return datetime.utcnow()


def _money(v: Any) -> Decimal:
    try:
        return Decimal(str(v or 0))
    except Exception:
        return Decimal("0")


def _amount_of(opp: SalesOpportunity) -> Decimal:
    if getattr(opp, "final_amount", None) is not None:
        return _money(opp.final_amount)
    return _money(getattr(opp, "estimated_amount", 0))


ACTIVE_TASK = ("todo", "in_progress")
ACTIVITY_TYPES = ("call", "email", "meeting", "visit")


class InsightRulesEngine:
    """Bounded scans — never all orgs, never unbounded history."""

    MAX_OPPORTUNITIES = 120
    MAX_TASKS = 80
    MAX_PROPOSALS = 80
    MAX_ACTIVITIES_LOOKBACK = 200

    def __init__(self, db: Session):
        self.db = db

    def collect(self, organization_id: int) -> list[InsightDraft]:
        now = _now()
        drafts: list[InsightDraft] = []
        opps = self._open_opportunities(organization_id)
        stages = {s.id: s for s in self._stages_for_opps(opps)}
        activity_index = self._activity_index(organization_id, [o.id for o in opps], now)
        task_index = self._task_index(organization_id, [o.id for o in opps], now)
        proposal_by_opp = self._proposals_by_opportunity(organization_id)

        drafts.extend(self._task_rules(organization_id, now))
        drafts.extend(self._meeting_rules(organization_id, now))
        drafts.extend(
            self._opportunity_rules(
                opps, stages, activity_index, task_index, proposal_by_opp, now
            )
        )
        drafts.extend(self._pipeline_rules(opps, stages, activity_index, task_index, now))
        drafts.extend(self._proposal_rules(organization_id, now))
        drafts.extend(self._activity_day_rules(organization_id, opps, now))
        return drafts

    def _open_opportunities(self, organization_id: int) -> list[SalesOpportunity]:
        return (
            soft_alive(self.db.query(SalesOpportunity), SalesOpportunity)
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == "open",
            )
            .order_by(SalesOpportunity.updated_at.desc())
            .limit(self.MAX_OPPORTUNITIES)
            .all()
        )

    def _stages_for_opps(self, opps: list[SalesOpportunity]) -> list[SalesPipelineStage]:
        ids = {o.stage_id for o in opps if o.stage_id}
        if not ids:
            return []
        return (
            self.db.query(SalesPipelineStage)
            .filter(SalesPipelineStage.id.in_(ids))
            .all()
        )

    def _activity_index(
        self, organization_id: int, opp_ids: list[int], now: datetime
    ) -> dict[int, dict[str, Any]]:
        index: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"last": None, "next": None, "has_open_task": False}
        )
        if not opp_ids:
            return index
        rows = (
            soft_alive(self.db.query(SalesActivity), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.opportunity_id.in_(opp_ids),
            )
            .order_by(SalesActivity.activity_at.desc())
            .limit(self.MAX_ACTIVITIES_LOOKBACK)
            .all()
        )
        for a in rows:
            oid = a.opportunity_id
            if oid is None:
                continue
            if a.activity_at and a.activity_at <= now:
                if index[oid]["last"] is None or a.activity_at > index[oid]["last"]:
                    index[oid]["last"] = a.activity_at
            if a.activity_at and a.activity_at >= now:
                if index[oid]["next"] is None or a.activity_at < index[oid]["next"]:
                    index[oid]["next"] = a.activity_at
        return index

    def _task_index(
        self, organization_id: int, opp_ids: list[int], now: datetime
    ) -> dict[int, list[SalesTask]]:
        index: dict[int, list[SalesTask]] = defaultdict(list)
        if not opp_ids:
            return index
        rows = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.opportunity_id.in_(opp_ids),
                SalesTask.status.in_(ACTIVE_TASK),
            )
            .limit(self.MAX_TASKS)
            .all()
        )
        for t in rows:
            if t.opportunity_id:
                index[t.opportunity_id].append(t)
        return index

    def _proposals_by_opportunity(
        self, organization_id: int
    ) -> dict[int, list[CommercialProposal]]:
        rows = (
            self.db.query(CommercialProposal)
            .filter(
                CommercialProposal.organization_id == organization_id,
                CommercialProposal.deleted_at.is_(None),
                CommercialProposal.opportunity_id.isnot(None),
            )
            .order_by(CommercialProposal.updated_at.desc())
            .limit(self.MAX_PROPOSALS)
            .all()
        )
        by_opp: dict[int, list[CommercialProposal]] = defaultdict(list)
        for p in rows:
            if p.opportunity_id:
                by_opp[p.opportunity_id].append(p)
        return by_opp

    def _finalize(self, draft: InsightDraft) -> InsightDraft:
        if draft.insight_type in ACTIONABLE_DECISION_TYPES and draft.severity in (
            InsightSeverity.high.value,
            InsightSeverity.critical.value,
        ):
            draft.project_decision = True
        if draft.insight_type in NOTIFIABLE_TYPES and draft.severity in (
            InsightSeverity.high.value,
            InsightSeverity.critical.value,
        ):
            draft.notify = True
        return draft

    # ----- Tasks -----

    def _task_rules(self, organization_id: int, now: datetime) -> list[InsightDraft]:
        drafts: list[InsightDraft] = []
        tasks = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.status.in_(ACTIVE_TASK),
                SalesTask.due_at.isnot(None),
                SalesTask.due_at < now,
            )
            .order_by(SalesTask.due_at.asc())
            .limit(self.MAX_TASKS)
            .all()
        )
        # Critical = priority high overdue
        critical = [t for t in tasks if (t.priority or "").lower() in ("high", "critical", "urgent")]
        by_opp: dict[int, list[SalesTask]] = defaultdict(list)
        for t in tasks:
            if t.opportunity_id:
                by_opp[t.opportunity_id].append(t)

        for t in critical[:15]:
            days_late = max(0, (now - t.due_at).days) if t.due_at else 0
            sev = InsightSeverity.critical.value if days_late >= 2 else InsightSeverity.high.value
            route = "/sales/tasks"
            if t.opportunity_id:
                route = f"/sales/deals/{t.opportunity_id}"
            primary = action(
                action_type="create_task" if False else "open_opportunity",
                label="Ouvrir la tâche / le deal",
                route=route,
                required_permission="sales.write",
                expected_resolution_behavior="task_completed",
            )
            if not t.opportunity_id:
                primary = action(
                    action_type="open_opportunity",
                    label="Ouvrir les tâches",
                    route="/sales/tasks",
                    required_permission="sales.read",
                    expected_resolution_behavior="task_completed",
                )
            drafts.append(
                self._finalize(
                    InsightDraft(
                        insight_type=InsightType.task_critical_overdue.value,
                        category=InsightCategory.task.value,
                        severity=sev,
                        priority_score=priority_score(
                            severity=sev, days_until_deadline=-days_late, impact_boost=10
                        ),
                        title=f"Tâche prioritaire en retard — {t.title}",
                        summary=f"La tâche « {t.title} » est en retard de {days_late} jour(s).",
                        explanation=explanation(
                            headline="Une tâche prioritaire est en retard",
                            observed_facts=[
                                f"Titre : {t.title}",
                                f"Échéance dépassée de {days_late} jour(s)",
                                f"Priorité : {t.priority or 'high'}",
                            ],
                            rule_applied="Tâche à priorité élevée avec échéance dépassée",
                            why_it_matters="Les actions prioritaires non traitées retardent la progression commerciale.",
                            recommended_next_step="Traiter ou replanifier la tâche.",
                            resolution_condition="La tâche est terminée ou son échéance est mise à jour dans le futur.",
                        ),
                        evidence=[
                            evidence_item(
                                type="overdue_task_count",
                                label="Jours de retard",
                                value=days_late,
                                source="sales_task",
                            ),
                            evidence_item(
                                type="task_priority",
                                label="Priorité",
                                value=t.priority or "high",
                                source="sales_task",
                            ),
                        ],
                        source_type="sales_task",
                        source_id=str(t.id),
                        source_label=t.title,
                        deduplication_key=f"task_critical_overdue:{t.id}",
                        route=route,
                        recommended_action=primary,
                        available_actions=standard_actions(primary=primary, can_dismiss=False),
                        resolution_condition="Tâche terminée ou échéance future",
                        observed_value=str(days_late),
                    )
                )
            )

        for oid, group in by_opp.items():
            overdue = [t for t in group if t.due_at and t.due_at < now]
            if len(overdue) < 2:
                continue
            sev = InsightSeverity.high.value
            route = f"/sales/deals/{oid}"
            primary = action(
                action_type="open_opportunity",
                label="Ouvrir le deal",
                route=route,
                required_permission="sales.read",
                expected_resolution_behavior="tasks_completed",
            )
            drafts.append(
                self._finalize(
                    InsightDraft(
                        insight_type=InsightType.tasks_overdue_on_deal.value,
                        category=InsightCategory.task.value,
                        severity=sev,
                        priority_score=priority_score(severity=sev, impact_boost=5),
                        title=f"{len(overdue)} tâches en retard sur un deal",
                        summary=f"{len(overdue)} tâches actives sont en retard sur la même opportunité.",
                        explanation=explanation(
                            headline="Plusieurs tâches en retard sur le même deal",
                            observed_facts=[f"Nombre de tâches en retard : {len(overdue)}"],
                            rule_applied="≥ 2 tâches actives en retard sur une opportunité",
                            why_it_matters="L’accumulation de retards freine la clôture.",
                            recommended_next_step="Prioriser et clôturer les tâches du deal.",
                            resolution_condition="Moins de 2 tâches en retard sur ce deal.",
                        ),
                        evidence=[
                            evidence_item(
                                type="overdue_task_count",
                                label="Tâches en retard",
                                value=len(overdue),
                                source="sales_task",
                            )
                        ],
                        source_type="sales_opportunity",
                        source_id=str(oid),
                        source_label=f"Deal #{oid}",
                        deduplication_key=f"tasks_overdue_on_deal:{oid}",
                        route=route,
                        recommended_action=primary,
                        available_actions=standard_actions(primary=primary),
                        resolution_condition="< 2 tâches en retard",
                    )
                )
            )
        return drafts

    def _meeting_rules(self, organization_id: int, now: datetime) -> list[InsightDraft]:
        drafts: list[InsightDraft] = []
        horizon = now + timedelta(hours=MEETING_IMMINENT_HOURS)
        meetings = (
            soft_alive(self.db.query(SalesActivity), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.activity_type == "meeting",
                SalesActivity.activity_at >= now,
                SalesActivity.activity_at <= horizon,
            )
            .order_by(SalesActivity.activity_at.asc())
            .limit(10)
            .all()
        )
        for m in meetings:
            sev = InsightSeverity.high.value
            route = f"/sales/deals/{m.opportunity_id}" if m.opportunity_id else "/sales/activities"
            primary = action(
                action_type="create_activity",
                label="Préparer le rendez-vous",
                route=route,
                required_permission="sales.read",
                expected_resolution_behavior="meeting_passed",
            )
            hours = max(0, int((m.activity_at - now).total_seconds() // 3600)) if m.activity_at else 0
            drafts.append(
                self._finalize(
                    InsightDraft(
                        insight_type=InsightType.meeting_imminent.value,
                        category=InsightCategory.activity.value,
                        severity=sev,
                        priority_score=priority_score(
                            severity=sev, days_until_deadline=0, impact_boost=8
                        ),
                        title=f"Rendez-vous imminent — {m.subject or 'Réunion'}",
                        summary=f"Une réunion est planifiée dans environ {hours} h.",
                        explanation=explanation(
                            headline="Un rendez-vous arrive bientôt",
                            observed_facts=[
                                f"Sujet : {m.subject or 'Réunion'}",
                                f"Dans environ {hours} heure(s)",
                            ],
                            rule_applied=f"Réunion dans les {MEETING_IMMINENT_HOURS} prochaines heures",
                            why_it_matters="La préparation immédiate améliore le taux de progression.",
                            recommended_next_step="Ouvrir le deal ou le dossier lié et préparer l’échange.",
                            resolution_condition="La réunion est passée ou reportée.",
                        ),
                        evidence=[
                            evidence_item(
                                type="meeting_at",
                                label="Heure prévue",
                                value=m.activity_at.isoformat() if m.activity_at else None,
                                source="sales_activity",
                            )
                        ],
                        source_type="sales_activity",
                        source_id=str(m.id),
                        source_label=m.subject or "Réunion",
                        deduplication_key=f"meeting_imminent:{m.id}",
                        route=route,
                        recommended_action=primary,
                        available_actions=standard_actions(primary=primary),
                        resolution_condition="Réunion passée",
                    )
                )
            )
        return drafts

    # ----- Opportunities -----

    def _opportunity_rules(
        self,
        opps: list[SalesOpportunity],
        stages: dict[int, SalesPipelineStage],
        activity_index: dict[int, dict[str, Any]],
        task_index: dict[int, list[SalesTask]],
        proposal_by_opp: dict[int, list[CommercialProposal]],
        now: datetime,
    ) -> list[InsightDraft]:
        drafts: list[InsightDraft] = []
        for opp in opps:
            stage = stages.get(opp.stage_id) if opp.stage_id else None
            act = activity_index.get(opp.id) or {"last": None, "next": None}
            tasks = task_index.get(opp.id) or []
            last_at = act.get("last")
            next_at = act.get("next")
            days = days_in_stage(opp.stage_entered_at, now)
            amount = _amount_of(opp)
            health, _label = health_score_for(
                days=days,
                has_contact=bool(opp.person_id),
                has_company=bool(opp.company_id),
                last_activity_at=last_at,
                next_activity_at=next_at,
                has_open_task=bool(tasks),
                probability=int(opp.probability or 0),
                stage_probability=int(stage.probability if stage else 0),
                now=now,
            )
            risk, _ = risk_level_for(
                days=days,
                health=health,
                last_activity_at=last_at,
                expected_close=getattr(opp, "expected_close_date", None),
                probability=int(opp.probability or 0),
                now=now,
            )
            inactive_days = (now - last_at).days if last_at else 999
            route = f"/sales/deals/{opp.id}"

            # 1 High-value inactive
            if amount >= HIGH_VALUE_AMOUNT and inactive_days >= INACTIVE_DAYS:
                sev = severity_for_inactive_high_value(
                    days_inactive=inactive_days, amount=amount
                )
                primary = action(
                    action_type="create_activity",
                    label="Planifier une relance",
                    route=route,
                    required_permission="sales.write",
                    expected_resolution_behavior="new_activity",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.opportunity_inactive_high_value.value,
                            category=InsightCategory.opportunity.value,
                            severity=sev,
                            priority_score=priority_score(
                                severity=sev,
                                amount=amount,
                                days_inactive=inactive_days,
                            ),
                            title=f"Opportunité importante inactive — {opp.name}",
                            summary=(
                                f"Opportunité de {amount} € sans activité depuis "
                                f"{inactive_days if inactive_days < 999 else 'longtemps'} jours."
                            ),
                            explanation=explanation(
                                headline="Cette opportunité nécessite une relance",
                                observed_facts=[
                                    f"Montant : {amount} €",
                                    f"Dernière activité : il y a {inactive_days if inactive_days < 999 else '—'} jours",
                                    f"Health : {health}/100",
                                ],
                                rule_applied=(
                                    f"Opportunité ≥ {HIGH_VALUE_AMOUNT} € sans activité "
                                    f"depuis plus de {INACTIVE_DAYS} jours"
                                ),
                                why_it_matters="Le risque de perte augmente lorsque la négociation reste inactive.",
                                recommended_next_step="Planifier un appel ou une réunion.",
                                resolution_condition="Une nouvelle activité est enregistrée.",
                            ),
                            evidence=[
                                evidence_item(type="amount", label="Montant", value=float(amount), source="opportunity"),
                                evidence_item(type="last_activity_age", label="Jours sans activité", value=inactive_days if inactive_days < 999 else None, source="activity"),
                                evidence_item(type="health_score", label="Health", value=health, source="pipeline_service"),
                            ],
                            source_type="sales_opportunity",
                            source_id=str(opp.id),
                            source_label=opp.name,
                            deduplication_key=f"opportunity_inactive_high_value:{opp.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Nouvelle activité enregistrée",
                            observed_value=str(inactive_days),
                            score=health,
                        )
                    )
                )

            # 2 No next action
            if next_at is None and not tasks:
                sev = (
                    InsightSeverity.high.value
                    if amount >= HIGH_VALUE_AMOUNT
                    else InsightSeverity.medium.value
                )
                primary = action(
                    action_type="create_task",
                    label="Créer une prochaine action",
                    route=route,
                    required_permission="sales.write",
                    expected_resolution_behavior="next_action_created",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.opportunity_no_next_action.value,
                            category=InsightCategory.opportunity.value,
                            severity=sev,
                            priority_score=priority_score(severity=sev, amount=amount),
                            title=f"Aucune prochaine action — {opp.name}",
                            summary="Aucune activité future ni tâche ouverte n’est planifiée.",
                            explanation=explanation(
                                headline="Aucune prochaine action planifiée",
                                observed_facts=[
                                    f"Opportunité : {opp.name}",
                                    f"Montant : {amount} €",
                                    "Aucune activité future",
                                    "Aucune tâche ouverte",
                                ],
                                rule_applied="Opportunité ouverte sans activité future ni tâche active",
                                why_it_matters="Sans prochaine étape, le deal stagne dans le pipeline.",
                                recommended_next_step="Créer une tâche ou planifier une activité.",
                                resolution_condition="Une activité future ou une tâche ouverte existe.",
                            ),
                            evidence=[
                                evidence_item(type="amount", label="Montant", value=float(amount), source="opportunity"),
                            ],
                            source_type="sales_opportunity",
                            source_id=str(opp.id),
                            source_label=opp.name,
                            deduplication_key=f"opportunity_no_next_action:{opp.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Prochaine action créée",
                            score=health,
                        )
                    )
                )

            # 3 Stage aging
            if days >= STAGE_AGING_DAYS and stage and not stage.is_won and not stage.is_lost:
                sev = (
                    InsightSeverity.high.value
                    if days >= STAGE_AGING_CRITICAL_DAYS
                    else InsightSeverity.medium.value
                )
                primary = action(
                    action_type="open_pipeline",
                    label="Revoir l’étape",
                    route=route,
                    required_permission="sales.read",
                    expected_resolution_behavior="stage_moved_or_activity",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.opportunity_stage_aging.value,
                            category=InsightCategory.opportunity.value,
                            severity=sev,
                            priority_score=priority_score(
                                severity=sev, amount=amount, days_inactive=days
                            ),
                            title=f"Trop longtemps en étape — {opp.name}",
                            summary=f"{days} jours dans l’étape « {stage.name} ».",
                            explanation=explanation(
                                headline="Vieillissement élevé dans l’étape",
                                observed_facts=[
                                    f"Étape : {stage.name}",
                                    f"Jours dans l’étape : {days}",
                                    f"Risque pipeline : {risk}",
                                ],
                                rule_applied=f"Jours dans l’étape ≥ {STAGE_AGING_DAYS}",
                                why_it_matters="Un vieillissement prolongé indique souvent un blocage.",
                                recommended_next_step="Avancer l’étape, relancer ou requalifier.",
                                resolution_condition="Changement d’étape ou nouvelle activité récente.",
                            ),
                            evidence=[
                                evidence_item(type="stage_age", label="Jours en étape", value=days, source="opportunity"),
                                evidence_item(type="risk_level", label="Risque", value=risk, source="pipeline_service"),
                            ],
                            source_type="sales_opportunity",
                            source_id=str(opp.id),
                            source_label=opp.name,
                            deduplication_key=f"opportunity_stage_aging:{opp.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Étape changée ou activité récente",
                            observed_value=str(days),
                            score=health,
                        )
                    )
                )

            # 4 Closing overdue
            close = getattr(opp, "expected_close_date", None)
            if close and isinstance(close, date) and close < now.date():
                sev = InsightSeverity.high.value
                primary = action(
                    action_type="open_opportunity",
                    label="Mettre à jour la date de closing",
                    route=route,
                    required_permission="sales.write",
                    expected_resolution_behavior="close_date_updated",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.opportunity_closing_overdue.value,
                            category=InsightCategory.opportunity.value,
                            severity=sev,
                            priority_score=priority_score(
                                severity=sev, amount=amount, days_until_deadline=-1
                            ),
                            title=f"Date de closing dépassée — {opp.name}",
                            summary=f"Closing prévu le {close.isoformat()} — date dépassée.",
                            explanation=explanation(
                                headline="La date de closing est dépassée",
                                observed_facts=[
                                    f"Closing prévu : {close.isoformat()}",
                                    f"Montant : {amount} €",
                                ],
                                rule_applied="expected_close_date < aujourd’hui",
                                why_it_matters="Une date dépassée fausse le forecast et le suivi.",
                                recommended_next_step="Mettre à jour la date ou clôturer l’opportunité.",
                                resolution_condition="Date future ou opportunité gagnée/perdue.",
                            ),
                            evidence=[
                                evidence_item(
                                    type="close_date",
                                    label="Closing",
                                    value=close.isoformat(),
                                    source="opportunity",
                                )
                            ],
                            source_type="sales_opportunity",
                            source_id=str(opp.id),
                            source_label=opp.name,
                            deduplication_key=f"opportunity_closing_overdue:{opp.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Date mise à jour ou deal clos",
                        )
                    )
                )

            # 5 Low health + high value
            if amount >= HIGH_VALUE_AMOUNT and health < LOW_HEALTH:
                sev = InsightSeverity.high.value
                primary = action(
                    action_type="open_opportunity",
                    label="Renforcer le deal",
                    route=route,
                    required_permission="sales.read",
                    expected_resolution_behavior="health_improved",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.opportunity_low_health_high_value.value,
                            category=InsightCategory.opportunity.value,
                            severity=sev,
                            priority_score=priority_score(severity=sev, amount=amount),
                            title=f"Santé faible sur un montant élevé — {opp.name}",
                            summary=f"Health {health}/100 pour {amount} €.",
                            explanation=explanation(
                                headline="Forte valeur avec santé fragile",
                                observed_facts=[
                                    f"Health : {health}/100",
                                    f"Montant : {amount} €",
                                    f"Risque : {risk}",
                                ],
                                rule_applied=f"Montant ≥ {HIGH_VALUE_AMOUNT} € et Health < {LOW_HEALTH}",
                                why_it_matters="Les deals fragiles à forte valeur méritent une attention immédiate.",
                                recommended_next_step="Compléter contact, activité et prochaine action.",
                                resolution_condition=f"Health ≥ {LOW_HEALTH}",
                            ),
                            evidence=[
                                evidence_item(type="health_score", label="Health", value=health, source="pipeline_service"),
                                evidence_item(type="amount", label="Montant", value=float(amount), source="opportunity"),
                            ],
                            source_type="sales_opportunity",
                            source_id=str(opp.id),
                            source_label=opp.name,
                            deduplication_key=f"opportunity_low_health_high_value:{opp.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Health amélioré",
                            score=health,
                        )
                    )
                )

            # 6 Near close without proposal
            if close and isinstance(close, date):
                days_to_close = (close - now.date()).days
                props = proposal_by_opp.get(opp.id) or []
                active_props = [
                    p
                    for p in props
                    if p.status
                    not in (
                        ProposalStatus.cancelled.value,
                        ProposalStatus.rejected.value,
                        ProposalStatus.expired.value,
                    )
                ]
                if 0 <= days_to_close <= CLOSING_SOON_DAYS and not active_props:
                    sev = InsightSeverity.high.value
                    primary = action(
                        action_type="open_proposal",
                        label="Préparer une proposition",
                        route=f"/sales/proposals/new?opportunity_id={opp.id}",
                        required_permission="sales.proposals.write",
                        expected_resolution_behavior="proposal_created",
                    )
                    drafts.append(
                        self._finalize(
                            InsightDraft(
                                insight_type=InsightType.opportunity_no_proposal_near_close.value,
                                category=InsightCategory.proposal.value,
                                severity=sev,
                                priority_score=priority_score(
                                    severity=sev,
                                    amount=amount,
                                    days_until_deadline=days_to_close,
                                ),
                                title=f"Closing proche sans proposition — {opp.name}",
                                summary=f"Closing dans {days_to_close} jour(s) sans proposition active.",
                                explanation=explanation(
                                    headline="Closing proche sans proposition commerciale",
                                    observed_facts=[
                                        f"Jours avant closing : {days_to_close}",
                                        "Aucune proposition active",
                                    ],
                                    rule_applied=f"Closing ≤ {CLOSING_SOON_DAYS} jours et aucune proposition active",
                                    why_it_matters="Sans offre formalisée, la clôture est peu probable.",
                                    recommended_next_step="Créer une proposition commerciale.",
                                    resolution_condition="Une proposition active est liée.",
                                ),
                                evidence=[
                                    evidence_item(
                                        type="days_to_close",
                                        label="Jours avant closing",
                                        value=days_to_close,
                                        source="opportunity",
                                    )
                                ],
                                source_type="sales_opportunity",
                                source_id=str(opp.id),
                                source_label=opp.name,
                                deduplication_key=f"opportunity_no_proposal_near_close:{opp.id}",
                                route=route,
                                recommended_action=primary,
                                available_actions=standard_actions(primary=primary),
                                resolution_condition="Proposition créée",
                            )
                        )
                    )
        return drafts

    # ----- Pipeline aggregates -----

    def _pipeline_rules(
        self,
        opps: list[SalesOpportunity],
        stages: dict[int, SalesPipelineStage],
        activity_index: dict[int, dict[str, Any]],
        task_index: dict[int, list[SalesTask]],
        now: datetime,
    ) -> list[InsightDraft]:
        drafts: list[InsightDraft] = []
        if not opps:
            return drafts

        by_stage: dict[int, list[SalesOpportunity]] = defaultdict(list)
        for o in opps:
            if o.stage_id:
                by_stage[o.stage_id].append(o)

        for stage_id, group in by_stage.items():
            stage = stages.get(stage_id)
            if not stage or stage.is_won or stage.is_lost:
                continue
            if len(group) >= CONGESTED_STAGE_COUNT:
                sev = InsightSeverity.medium.value
                primary = action(
                    action_type="open_pipeline",
                    label="Examiner le pipeline",
                    route="/sales/pipeline",
                    required_permission="sales.read",
                    expected_resolution_behavior="stage_cleared",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.pipeline_stage_congested.value,
                            category=InsightCategory.pipeline.value,
                            severity=sev,
                            priority_score=priority_score(severity=sev, impact_boost=4),
                            title=f"Étape congestionnée — {stage.name}",
                            summary=f"{len(group)} opportunités ouvertes dans « {stage.name} ».",
                            explanation=explanation(
                                headline="Une étape du pipeline est congestionnée",
                                observed_facts=[
                                    f"Étape : {stage.name}",
                                    f"Nombre d’opportunités : {len(group)}",
                                    f"Seuil absolu documenté : {CONGESTED_STAGE_COUNT}",
                                ],
                                rule_applied=f"≥ {CONGESTED_STAGE_COUNT} opportunités ouvertes dans une étape",
                                why_it_matters="La congestion ralentit la progression globale du pipeline.",
                                recommended_next_step="Revoir les deals de cette étape et débloquer les plus anciens.",
                                resolution_condition=f"< {CONGESTED_STAGE_COUNT} opportunités dans l’étape",
                            ),
                            evidence=[
                                evidence_item(
                                    type="stage_count",
                                    label="Opportunités dans l’étape",
                                    value=len(group),
                                    source="pipeline",
                                )
                            ],
                            source_type="sales_pipeline_stage",
                            source_id=str(stage_id),
                            source_label=stage.name,
                            deduplication_key=f"pipeline_stage_congested:{stage_id}",
                            route="/sales/pipeline",
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Congestion résorbée",
                        )
                    )
                )

        without_next = 0
        high_risk = 0
        for opp in opps:
            act = activity_index.get(opp.id) or {}
            tasks = task_index.get(opp.id) or []
            if act.get("next") is None and not tasks:
                without_next += 1
            stage = stages.get(opp.stage_id) if opp.stage_id else None
            days = days_in_stage(opp.stage_entered_at, now)
            health, _ = health_score_for(
                days=days,
                has_contact=bool(opp.person_id),
                has_company=bool(opp.company_id),
                last_activity_at=act.get("last"),
                next_activity_at=act.get("next"),
                has_open_task=bool(tasks),
                probability=int(opp.probability or 0),
                stage_probability=int(stage.probability if stage else 0),
                now=now,
            )
            risk, _ = risk_level_for(
                days=days,
                health=health,
                last_activity_at=act.get("last"),
                expected_close=getattr(opp, "expected_close_date", None),
                probability=int(opp.probability or 0),
                now=now,
            )
            if risk in ("high", "critical"):
                high_risk += 1

        if without_next >= MANY_WITHOUT_NEXT_ACTION:
            sev = InsightSeverity.medium.value
            primary = action(
                action_type="open_pipeline",
                label="Planifier les prochaines actions",
                route="/sales/pipeline",
                required_permission="sales.write",
                expected_resolution_behavior="next_actions_created",
            )
            drafts.append(
                self._finalize(
                    InsightDraft(
                        insight_type=InsightType.pipeline_many_without_next_action.value,
                        category=InsightCategory.pipeline.value,
                        severity=sev,
                        priority_score=priority_score(severity=sev, impact_boost=3),
                        title="Trop d’opportunités sans prochaine action",
                        summary=f"{without_next} opportunités ouvertes n’ont aucune prochaine action.",
                        explanation=explanation(
                            headline="Le pipeline manque de prochaines actions",
                            observed_facts=[
                                f"Opportunités sans prochaine action : {without_next}",
                                f"Seuil : {MANY_WITHOUT_NEXT_ACTION}",
                            ],
                            rule_applied=f"≥ {MANY_WITHOUT_NEXT_ACTION} opportunités sans next action",
                            why_it_matters="Sans prochaines étapes, le pipeline devient passif.",
                            recommended_next_step="Parcourir le pipeline et créer des actions.",
                            resolution_condition=f"< {MANY_WITHOUT_NEXT_ACTION} deals sans next action",
                        ),
                        evidence=[
                            evidence_item(
                                type="without_next_action_count",
                                label="Sans prochaine action",
                                value=without_next,
                                source="pipeline",
                            )
                        ],
                        source_type="sales_pipeline",
                        source_id="open",
                        source_label="Pipeline ouvert",
                        deduplication_key="pipeline_many_without_next_action:open",
                        route="/sales/pipeline",
                        recommended_action=primary,
                        available_actions=standard_actions(primary=primary),
                        resolution_condition="Moins de deals sans next action",
                    )
                )
            )

        if opps and (high_risk / len(opps)) >= HIGH_RISK_SHARE:
            sev = InsightSeverity.medium.value
            primary = action(
                action_type="open_pipeline",
                label="Traiter les deals à risque",
                route="/sales/pipeline",
                required_permission="sales.read",
                expected_resolution_behavior="risk_reduced",
            )
            drafts.append(
                self._finalize(
                    InsightDraft(
                        insight_type=InsightType.pipeline_high_risk_concentration.value,
                        category=InsightCategory.pipeline.value,
                        severity=sev,
                        priority_score=priority_score(severity=sev, impact_boost=5),
                        title="Concentration de deals à risque",
                        summary=f"{high_risk}/{len(opps)} opportunités sont à risque élevé ou critique.",
                        explanation=explanation(
                            headline="Trop d’opportunités à risque dans le pipeline",
                            observed_facts=[
                                f"Deals à risque : {high_risk}",
                                f"Total ouverts : {len(opps)}",
                                f"Seuil de part : {int(HIGH_RISK_SHARE * 100)} %",
                            ],
                            rule_applied=f"Part high/critical ≥ {int(HIGH_RISK_SHARE * 100)} %",
                            why_it_matters="Une forte concentration de risque menace le forecast.",
                            recommended_next_step="Prioriser les deals critical/high du pipeline.",
                            resolution_condition="Part de risque sous le seuil",
                        ),
                        evidence=[
                            evidence_item(
                                type="high_risk_count",
                                label="Deals à risque",
                                value=high_risk,
                                source="pipeline",
                            )
                        ],
                        source_type="sales_pipeline",
                        source_id="risk",
                        source_label="Pipeline risque",
                        deduplication_key="pipeline_high_risk_concentration:open",
                        route="/sales/pipeline",
                        recommended_action=primary,
                        available_actions=standard_actions(primary=primary),
                        resolution_condition="Part de risque réduite",
                    )
                )
            )
        return drafts

    # ----- Proposals -----

    def _proposal_rules(self, organization_id: int, now: datetime) -> list[InsightDraft]:
        drafts: list[InsightDraft] = []
        proposals = (
            self.db.query(CommercialProposal)
            .filter(
                CommercialProposal.organization_id == organization_id,
                CommercialProposal.deleted_at.is_(None),
                CommercialProposal.status.notin_(
                    (
                        ProposalStatus.cancelled.value,
                        ProposalStatus.converted.value,
                    )
                ),
            )
            .order_by(CommercialProposal.updated_at.desc())
            .limit(self.MAX_PROPOSALS)
            .all()
        )
        for p in proposals:
            version = None
            if p.current_version_id:
                version = self.db.get(CommercialProposalVersion, p.current_version_id)
            route = f"/sales/proposals/{p.id}"
            amount = _money(version.total) if version else Decimal("0")
            valid_until = p.valid_until or (version.valid_until if version else None)

            if p.status == ProposalStatus.approved.value:
                sev = InsightSeverity.high.value
                primary = action(
                    action_type="open_proposal",
                    label="Générer / envoyer la proposition",
                    route=route,
                    required_permission="sales.proposals.send",
                    expected_resolution_behavior="proposal_sent",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=InsightType.proposal_approved_unsent.value,
                            category=InsightCategory.proposal.value,
                            severity=sev,
                            priority_score=priority_score(severity=sev, amount=amount),
                            title=f"Proposition approuvée non envoyée — {p.proposal_number}",
                            summary="La proposition est approuvée mais pas encore envoyée.",
                            explanation=explanation(
                                headline="Proposition approuvée en attente d’envoi",
                                observed_facts=[
                                    f"Numéro : {p.proposal_number}",
                                    "Statut : approved",
                                ],
                                rule_applied="status == approved",
                                why_it_matters="Une offre approuvée non envoyée bloque la chaîne commerciale.",
                                recommended_next_step="Générer le PDF puis marquer comme envoyée.",
                                resolution_condition="Statut passé à sent (ou suivant).",
                            ),
                            evidence=[
                                evidence_item(type="proposal_status", label="Statut", value=p.status, source="proposal"),
                            ],
                            source_type="sales_proposal",
                            source_id=str(p.id),
                            source_label=p.proposal_number,
                            deduplication_key=f"proposal_approved_unsent:{p.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(primary=primary),
                            resolution_condition="Proposition envoyée",
                        )
                    )
                )

            if valid_until and isinstance(valid_until, date):
                days_left = (valid_until - now.date()).days
                if 0 <= days_left <= PROPOSAL_EXPIRING_DAYS and p.status in (
                    ProposalStatus.sent.value,
                    ProposalStatus.viewed.value,
                    ProposalStatus.negotiating.value,
                    ProposalStatus.approved.value,
                ):
                    sev = (
                        InsightSeverity.critical.value
                        if days_left == 0 and amount >= HIGH_VALUE_AMOUNT
                        else InsightSeverity.high.value
                    )
                    primary = action(
                        action_type="open_proposal",
                        label="Suivre la proposition",
                        route=route,
                        required_permission="sales.proposals.read",
                        expected_resolution_behavior="proposal_accepted_or_extended",
                    )
                    drafts.append(
                        self._finalize(
                            InsightDraft(
                                insight_type=InsightType.proposal_expiring_soon.value,
                                category=InsightCategory.proposal.value,
                                severity=sev,
                                priority_score=priority_score(
                                    severity=sev,
                                    amount=amount,
                                    days_until_deadline=days_left,
                                ),
                                title=f"Proposition expirant bientôt — {p.proposal_number}",
                                summary=f"Expire dans {days_left} jour(s) ({valid_until.isoformat()}).",
                                explanation=explanation(
                                    headline="Une proposition arrive à échéance",
                                    observed_facts=[
                                        f"Validité : {valid_until.isoformat()}",
                                        f"Jours restants : {days_left}",
                                        f"Montant : {amount} €",
                                    ],
                                    rule_applied=f"valid_until dans ≤ {PROPOSAL_EXPIRING_DAYS} jours",
                                    why_it_matters="Une offre qui expire sans suivi perd de la valeur commerciale.",
                                    recommended_next_step="Relancer le client ou prolonger la validité.",
                                    resolution_condition="Acceptée, prolongée, ou hors fenêtre d’expiration.",
                                ),
                                evidence=[
                                    evidence_item(
                                        type="valid_until",
                                        label="Validité",
                                        value=valid_until.isoformat(),
                                        source="proposal",
                                    )
                                ],
                                source_type="sales_proposal",
                                source_id=str(p.id),
                                source_label=p.proposal_number,
                                deduplication_key=f"proposal_expiring_soon:{p.id}",
                                route=route,
                                recommended_action=primary,
                                available_actions=standard_actions(primary=primary),
                                resolution_condition="Hors fenêtre d’expiration",
                            )
                        )
                    )

            if p.status == ProposalStatus.expired.value and p.opportunity_id:
                opp = self.db.get(SalesOpportunity, p.opportunity_id)
                if opp and opp.status == "open" and opp.deleted_at is None:
                    sev = InsightSeverity.medium.value
                    primary = action(
                        action_type="open_proposal",
                        label="Créer une nouvelle version",
                        route=route,
                        required_permission="sales.proposals.write",
                        expected_resolution_behavior="new_version_or_closed",
                    )
                    drafts.append(
                        self._finalize(
                            InsightDraft(
                                insight_type=InsightType.proposal_expired_open_opportunity.value,
                                category=InsightCategory.proposal.value,
                                severity=sev,
                                priority_score=priority_score(severity=sev, amount=amount),
                                title=f"Proposition expirée — opportunité encore ouverte",
                                summary=f"{p.proposal_number} est expirée alors que le deal reste ouvert.",
                                explanation=explanation(
                                    headline="Proposition expirée liée à une opportunité active",
                                    observed_facts=[
                                        f"Proposition : {p.proposal_number}",
                                        f"Opportunité : #{p.opportunity_id}",
                                    ],
                                    rule_applied="proposal expired + opportunity open",
                                    why_it_matters="Le deal reste ouvert sans offre valide.",
                                    recommended_next_step="Nouvelle version ou clôture de l’opportunité.",
                                    resolution_condition="Nouvelle proposition active ou deal clos.",
                                ),
                                evidence=[
                                    evidence_item(type="proposal_status", label="Statut", value=p.status, source="proposal"),
                                ],
                                source_type="sales_proposal",
                                source_id=str(p.id),
                                source_label=p.proposal_number,
                                deduplication_key=f"proposal_expired_open_opportunity:{p.id}",
                                route=route,
                                recommended_action=primary,
                                available_actions=standard_actions(primary=primary),
                                resolution_condition="Offre renouvelée ou deal clos",
                            )
                        )
                    )

            if p.status == ProposalStatus.negotiating.value and p.updated_at:
                days_neg = (now - p.updated_at).days
                if days_neg >= NEGOTIATION_LONG_DAYS:
                    sev = InsightSeverity.medium.value
                    primary = action(
                        action_type="open_proposal",
                        label="Relancer la négociation",
                        route=route,
                        required_permission="sales.proposals.read",
                        expected_resolution_behavior="status_advanced",
                    )
                    drafts.append(
                        self._finalize(
                            InsightDraft(
                                insight_type=InsightType.proposal_negotiation_long.value,
                                category=InsightCategory.proposal.value,
                                severity=sev,
                                priority_score=priority_score(
                                    severity=sev, amount=amount, days_inactive=days_neg
                                ),
                                title=f"Négociation longue — {p.proposal_number}",
                                summary=f"En négociation depuis {days_neg} jours sans avancée récente.",
                                explanation=explanation(
                                    headline="Négociation trop longue",
                                    observed_facts=[f"Jours depuis dernière mise à jour : {days_neg}"],
                                    rule_applied=f"status negotiating et inactivité ≥ {NEGOTIATION_LONG_DAYS} jours",
                                    why_it_matters="Les négociations prolongées perdent souvent en momentum.",
                                    recommended_next_step="Planifier une relance ou une nouvelle version.",
                                    resolution_condition="Statut avancé ou nouvelle version.",
                                ),
                                evidence=[
                                    evidence_item(type="negotiation_age", label="Jours", value=days_neg, source="proposal"),
                                ],
                                source_type="sales_proposal",
                                source_id=str(p.id),
                                source_label=p.proposal_number,
                                deduplication_key=f"proposal_negotiation_long:{p.id}",
                                route=route,
                                recommended_action=primary,
                                available_actions=standard_actions(primary=primary),
                                resolution_condition="Négociation avancée",
                            )
                        )
                    )

            if p.status == ProposalStatus.accepted.value and not p.linked_invoice_id:
                sev = InsightSeverity.high.value
                if getattr(p, "conversion_status", None) == "failed":
                    sev = InsightSeverity.critical.value
                    itype = InsightType.proposal_conversion_failed.value
                    title = f"Conversion échouée — {p.proposal_number}"
                    summary = "La conversion vers facture a échoué — intervention requise."
                    rule = "proposal accepted + conversion_status=failed"
                elif getattr(p, "conversion_status", None) == "ready" or p.linked_customer_id:
                    itype = InsightType.proposal_conversion_ready.value
                    title = f"Prête à convertir — {p.proposal_number}"
                    summary = "Cette proposition est prête à être convertie en facture brouillon."
                    rule = "proposal accepted + client résolu / ready"
                    sev = InsightSeverity.medium.value
                else:
                    itype = InsightType.proposal_accepted_unconverted.value
                    title = f"Acceptée non convertie — {p.proposal_number}"
                    summary = "Proposition acceptée sans facture brouillon liée."
                    rule = "proposal accepted + linked_invoice_id null"
                primary = action(
                    action_type="prepare_conversion",
                    label="Ouvrir la conversion",
                    route=route,
                    required_permission="sales.proposals.convert",
                    expected_resolution_behavior="converted",
                )
                drafts.append(
                    self._finalize(
                        InsightDraft(
                            insight_type=itype,
                            category=InsightCategory.conversion.value,
                            severity=sev,
                            priority_score=priority_score(severity=sev, amount=amount, impact_boost=8),
                            title=title,
                            summary=summary,
                            explanation=explanation(
                                headline=title,
                                observed_facts=[
                                    f"Statut proposition : {p.status}",
                                    f"Conversion : {getattr(p, 'conversion_status', None) or 'n/a'}",
                                    f"Client lié : {p.linked_customer_id or 'aucun'}",
                                ],
                                rule_applied=rule,
                                why_it_matters="La facturation brouillon finalise le cycle commercial contrôlé.",
                                recommended_next_step="Ouvrir le panneau de conversion et confirmer.",
                                resolution_condition="linked_invoice_id renseigné / status converted",
                            ),
                            evidence=[
                                evidence_item(
                                    type="conversion_status",
                                    label="Conversion",
                                    value=getattr(p, "conversion_status", None),
                                    source="proposal",
                                )
                            ],
                            source_type="sales_proposal",
                            source_id=str(p.id),
                            source_label=p.proposal_number,
                            deduplication_key=f"{itype}:{p.id}",
                            route=route,
                            recommended_action=primary,
                            available_actions=standard_actions(
                                primary=primary,
                                can_dismiss=sev != InsightSeverity.critical.value,
                            ),
                            resolution_condition="Proposition convertie",
                        )
                    )
                )

            if version and version.readiness_level in ("almost_ready", "incomplete"):
                blockers = []
                expl = version.readiness_explanation or {}
                if isinstance(expl, dict):
                    blockers = expl.get("blockers") or []
                if version.readiness_level == "almost_ready" and len(blockers) <= 1:
                    sev = InsightSeverity.low.value
                    primary = action(
                        action_type="open_proposal",
                        label="Compléter la proposition",
                        route=route,
                        required_permission="sales.proposals.write",
                        expected_resolution_behavior="readiness_ready",
                    )
                    drafts.append(
                        self._finalize(
                            InsightDraft(
                                insight_type=InsightType.proposal_almost_ready.value,
                                category=InsightCategory.proposal.value,
                                severity=sev,
                                priority_score=priority_score(severity=sev, amount=amount),
                                title=f"Presque prête — {p.proposal_number}",
                                summary="Un seul obstacle (ou presque) empêche la readiness.",
                                explanation=explanation(
                                    headline="Proposition presque prête",
                                    observed_facts=[
                                        f"Readiness : {version.readiness_score}/100",
                                        f"Niveau : {version.readiness_level}",
                                        f"Blockers : {len(blockers)}",
                                    ],
                                    rule_applied="almost_ready avec ≤ 1 blocker",
                                    why_it_matters="Un petit complément débloque l’envoi.",
                                    recommended_next_step="Corriger le blocker restant.",
                                    resolution_condition="readiness_level = ready",
                                ),
                                evidence=[
                                    evidence_item(
                                        type="readiness_score",
                                        label="Readiness",
                                        value=version.readiness_score,
                                        source="proposal_version",
                                    )
                                ],
                                source_type="sales_proposal",
                                source_id=str(p.id),
                                source_label=p.proposal_number,
                                deduplication_key=f"proposal_almost_ready:{p.id}",
                                route=route,
                                recommended_action=primary,
                                available_actions=standard_actions(primary=primary),
                                resolution_condition="Readiness ready",
                                score=version.readiness_score,
                            )
                        )
                    )
        return drafts

    def _activity_day_rules(
        self, organization_id: int, opps: list[SalesOpportunity], now: datetime
    ) -> list[InsightDraft]:
        if not opps:
            return []
        start = datetime.combine(now.date(), datetime.min.time())
        end = datetime.combine(now.date(), datetime.max.time())
        planned = (
            soft_alive(self.db.query(SalesActivity), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.activity_at >= start,
                SalesActivity.activity_at <= end,
            )
            .count()
        )
        if planned > 0:
            return []
        sev = InsightSeverity.info.value
        primary = action(
            action_type="create_activity",
            label="Planifier une activité",
            route="/sales/activities",
            required_permission="sales.write",
            expected_resolution_behavior="activity_today",
        )
        return [
            self._finalize(
                InsightDraft(
                    insight_type=InsightType.no_activity_planned_today.value,
                    category=InsightCategory.activity.value,
                    severity=sev,
                    priority_score=priority_score(severity=sev),
                    title="Aucune activité prévue aujourd’hui",
                    summary=f"{len(opps)} opportunités ouvertes, aucune activité planifiée aujourd’hui.",
                    explanation=explanation(
                        headline="Journée sans activité planifiée",
                        observed_facts=[
                            f"Opportunités ouvertes (échantillon) : {len(opps)}",
                            "Activités prévues aujourd’hui : 0",
                        ],
                        rule_applied="Opportunités ouvertes + 0 activité le jour courant",
                        why_it_matters="Une journée sans contact planifié réduit le momentum commercial.",
                        recommended_next_step="Planifier au moins une activité ou une tâche.",
                        resolution_condition="Au moins une activité planifiée aujourd’hui.",
                    ),
                    evidence=[
                        evidence_item(
                            type="activities_today",
                            label="Activités du jour",
                            value=0,
                            source="activity",
                        )
                    ],
                    source_type="sales_organization",
                    source_id=str(organization_id),
                    source_label="Organisation",
                    deduplication_key=f"no_activity_planned_today:{now.date().isoformat()}",
                    route="/sales/activities",
                    recommended_action=primary,
                    available_actions=standard_actions(primary=primary),
                    resolution_condition="Activité planifiée aujourd’hui",
                )
            )
        ]
