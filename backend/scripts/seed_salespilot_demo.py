#!/usr/bin/env python
"""Seed DEMO SalesPilot — développement uniquement, idempotent.

Usage (depuis backend/) :
  python -m scripts.seed_salespilot_demo
  python -m scripts.seed_salespilot_demo --organization-id 1
  python -m scripts.seed_salespilot_demo --purge

Marqueur : source / notes contenant DEMO_MARKER.
Ne crée jamais de données hors organisation cible.
Refuse production.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
DEMO_MARKER = "[DEMO SalesPilot]"
DEMO_SOURCE = "demo_salespilot"


def _assert_safe(settings: Any) -> None:
    env = (settings.app_env or "").strip().lower()
    if env in {"production", "prod"}:
        raise RuntimeError("REFUS: seed SalesPilot interdit en production")
    url = (settings.database_url or "").lower()
    if any(x in url for x in ("prod.", "production", "live.")) and not any(
        t in url for t in ("test", "dev", "demo", "sqlite", "local", "recette")
    ):
        raise RuntimeError(f"REFUS: DATABASE_URL suspecte ({settings.database_url!r})")


def _now() -> datetime:
    return datetime.utcnow()


def _resolve_org(db: Any, organization_id: int | None) -> tuple[Any, Any]:
    from app.models_saas import Organization, OrganizationMember, User

    if organization_id is not None:
        org = db.get(Organization, organization_id)
        if not org:
            raise RuntimeError(f"Organisation {organization_id} introuvable")
    else:
        org = (
            db.query(Organization)
            .filter(Organization.name.ilike("%demo%"))
            .order_by(Organization.id.asc())
            .first()
        )
        if org is None:
            org = db.query(Organization).order_by(Organization.id.asc()).first()
        if org is None:
            raise RuntimeError("Aucune organisation en base — créez un compte d'abord")

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.status == "active",
        )
        .order_by(OrganizationMember.id.asc())
        .first()
    )
    if member is None:
        member = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == org.id)
            .order_by(OrganizationMember.id.asc())
            .first()
        )
    if member is not None:
        user = db.get(User, member.user_id)
    else:
        user = db.query(User).order_by(User.id.asc()).first()
        if user is None:
            raise RuntimeError("Aucun utilisateur pour l'organisation")
        # Garantit un membership actif pour collab / assignations DEMO
        from app.models_saas import Role

        owner_role = db.query(Role).filter(Role.name == "owner").first()
        if owner_role is None:
            owner_role = db.query(Role).order_by(Role.id.asc()).first()
        if owner_role is None:
            raise RuntimeError("Aucun rôle RBAC — impossible de créer membership DEMO")
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role_id=owner_role.id,
            status="active",
        )
        db.add(member)
        db.flush()
        print(f"NOTE: membership DEMO créée user={user.id} org={org.id}")
    if user is None:
        raise RuntimeError("Aucun utilisateur pour l'organisation")
    return org, user


def _already_seeded(db: Any, organization_id: int) -> bool:
    from app.sales_crm.models import SalesLead

    n = (
        db.query(SalesLead)
        .filter(
            SalesLead.organization_id == organization_id,
            SalesLead.source == DEMO_SOURCE,
            SalesLead.deleted_at.is_(None),
        )
        .count()
    )
    return n >= 8


def purge_demo(db: Any, organization_id: int) -> dict[str, int]:
    """Supprime uniquement les entités marquées DEMO pour l'org."""
    from sqlalchemy import text

    counts: dict[str, int] = {}
    # Soft-delete / hard-delete ordered for FK safety — best effort by marker
    pairs = [
        ("sales_review_requests", "message"),
        ("sales_comments", "body"),
        ("sales_followers", None),  # via opportunity seed ids later
        ("sales_team_members", None),
        ("sales_teams", "description"),
        ("sales_insight_items", "title"),
        ("sales_commercial_proposal_events", None),
        ("sales_commercial_proposal_lines", None),
        ("sales_commercial_proposal_versions", "title"),
        ("sales_commercial_proposals", None),
        ("sales_notes", "body_markdown"),
        ("sales_tasks", "title"),
        ("sales_activities", "subject"),
        ("sales_opportunity_products", "name"),
        ("sales_opportunity_participants", None),
        ("sales_opportunities", "name"),
        ("sales_leads", "title"),
        ("sales_people", "first_name"),
        ("sales_companies", "name"),
    ]

    # Prefer ORM soft markers
    from app.sales_crm.models import (
        SalesActivity,
        SalesCompany,
        SalesLead,
        SalesNote,
        SalesOpportunity,
        SalesOpportunityParticipant,
        SalesOpportunityProduct,
        SalesPerson,
        SalesTask,
    )
    from app.sales_proposals.models import (
        CommercialProposal,
        CommercialProposalEvent,
        CommercialProposalLine,
        CommercialProposalVersion,
    )
    from app.sales_intelligence.models import SalesInsightItem
    from app.sales_collaboration.models import (
        SalesComment,
        SalesFollower,
        SalesReviewRequest,
        SalesTeam,
        SalesTeamMember,
    )

    def _soft_del(model: Any, *filters: Any) -> int:
        q = db.query(model).filter(model.organization_id == organization_id, *filters)
        n = 0
        for row in q.all():
            if hasattr(row, "deleted_at"):
                row.deleted_at = _now()
            else:
                db.delete(row)
            n += 1
        return n

    counts["companies"] = _soft_del(SalesCompany, SalesCompany.source == DEMO_SOURCE)
    counts["leads"] = _soft_del(SalesLead, SalesLead.source == DEMO_SOURCE)
    # People linked to DEMO companies or email @demo.salespilot.local
    people = (
        db.query(SalesPerson)
        .filter(
            SalesPerson.organization_id == organization_id,
            SalesPerson.deleted_at.is_(None),
            SalesPerson.email.ilike("%@demo.salespilot.local"),
        )
        .all()
    )
    for p in people:
        p.deleted_at = _now()
    counts["people"] = len(people)

    opps = (
        db.query(SalesOpportunity)
        .filter(
            SalesOpportunity.organization_id == organization_id,
            SalesOpportunity.source == DEMO_SOURCE,
            SalesOpportunity.deleted_at.is_(None),
        )
        .all()
    )
    opp_ids = [o.id for o in opps]
    for o in opps:
        o.deleted_at = _now()
    counts["opportunities"] = len(opps)

    if opp_ids:
        for model in (SalesOpportunityProduct, SalesOpportunityParticipant):
            for row in (
                db.query(model)
                .filter(model.organization_id == organization_id, model.opportunity_id.in_(opp_ids))
                .all()
            ):
                if hasattr(row, "deleted_at"):
                    row.deleted_at = _now()
                else:
                    db.delete(row)

    counts["activities"] = _soft_del(
        SalesActivity, SalesActivity.subject.ilike(f"%{DEMO_MARKER}%")
    )
    counts["tasks"] = _soft_del(SalesTask, SalesTask.title.ilike(f"%{DEMO_MARKER}%"))
    counts["notes"] = _soft_del(SalesNote, SalesNote.body_markdown.ilike(f"%{DEMO_MARKER}%"))

    props = (
        db.query(CommercialProposal)
        .filter(
            CommercialProposal.organization_id == organization_id,
            CommercialProposal.deleted_at.is_(None) if hasattr(CommercialProposal, "deleted_at") else True,
        )
        .all()
    )
    # Filter by DEMO title on versions
    demo_prop_ids: list[int] = []
    for prop in props:
        ver = (
            db.query(CommercialProposalVersion)
            .filter(CommercialProposalVersion.proposal_id == prop.id)
            .first()
        )
        if ver and DEMO_MARKER in (ver.title or ""):
            demo_prop_ids.append(prop.id)
    for pid in demo_prop_ids:
        db.query(CommercialProposalEvent).filter(
            CommercialProposalEvent.proposal_id == pid
        ).delete(synchronize_session=False)
        versions = (
            db.query(CommercialProposalVersion)
            .filter(CommercialProposalVersion.proposal_id == pid)
            .all()
        )
        for v in versions:
            lines = (
                db.query(CommercialProposalLine)
                .filter(CommercialProposalLine.proposal_version_id == v.id)
                .all()
            )
            for line in lines:
                db.delete(line)
            db.delete(v)
        prop = db.get(CommercialProposal, pid)
        if prop:
            db.delete(prop)
    counts["proposals"] = len(demo_prop_ids)

    counts["insights"] = _soft_del(
        SalesInsightItem, SalesInsightItem.title.ilike(f"%{DEMO_MARKER}%")
    ) if hasattr(SalesInsightItem, "deleted_at") else 0
    # Insights may not soft-delete — hard delete by title
    if counts["insights"] == 0:
        n = (
            db.query(SalesInsightItem)
            .filter(
                SalesInsightItem.organization_id == organization_id,
                SalesInsightItem.title.ilike(f"%{DEMO_MARKER}%"),
            )
            .delete(synchronize_session=False)
        )
        counts["insights"] = int(n or 0)

    teams = (
        db.query(SalesTeam)
        .filter(
            SalesTeam.organization_id == organization_id,
            SalesTeam.description.ilike(f"%{DEMO_MARKER}%"),
        )
        .all()
    )
    for t in teams:
        db.query(SalesTeamMember).filter(SalesTeamMember.team_id == t.id).delete(
            synchronize_session=False
        )
        if hasattr(t, "deleted_at"):
            t.deleted_at = _now()
        else:
            db.delete(t)
    counts["teams"] = len(teams)

    counts["comments"] = (
        db.query(SalesComment)
        .filter(
            SalesComment.organization_id == organization_id,
            SalesComment.body.ilike(f"%{DEMO_MARKER}%"),
        )
        .delete(synchronize_session=False)
    )
    counts["reviews"] = (
        db.query(SalesReviewRequest)
        .filter(
            SalesReviewRequest.organization_id == organization_id,
            SalesReviewRequest.message.ilike(f"%{DEMO_MARKER}%"),
        )
        .delete(synchronize_session=False)
    )
    # followers without marker — skip unless linked to demo opps
    if opp_ids:
        counts["followers"] = (
            db.query(SalesFollower)
            .filter(
                SalesFollower.organization_id == organization_id,
                SalesFollower.entity_type == "opportunity",
                SalesFollower.entity_id.in_(opp_ids),
            )
            .delete(synchronize_session=False)
        )
    else:
        counts["followers"] = 0

    _ = pairs, text  # reserved for future raw SQL fallback
    db.commit()
    return counts


def seed(db: Any, org: Any, user: Any) -> dict[str, Any]:
    from app.sales_crm.service import (
        create_activity,
        create_company,
        create_lead,
        create_note,
        create_opportunity,
        create_person,
        create_task,
        ensure_default_pipeline,
    )
    from app.sales_crm.deal_service import add_participant, add_product
    from app.sales_crm.models import SalesPipelineStage
    from app.sales_proposals.schemas import ProposalCreate
    from app.sales_proposals.service import ProposalService
    from app.sales_proposals.enums import ProposalStatus
    from app.sales_collaboration.schemas import (
        CommentCreate,
        FollowIn,
        ReviewCreate,
        TeamCreate,
        TeamMemberIn,
    )
    from app.sales_collaboration.service import SalesCollaborationService
    from app.sales_intelligence.service import SalesIntelligenceService

    org_id = org.id
    uid = user.id
    summary: dict[str, Any] = {"organization_id": org_id, "user_id": uid}

    pipeline = ensure_default_pipeline(db, organization_id=org_id, user_id=uid)
    stages = (
        db.query(SalesPipelineStage)
        .filter(
            SalesPipelineStage.pipeline_id == pipeline.id,
            SalesPipelineStage.organization_id == org_id,
            SalesPipelineStage.is_active.is_(True),
        )
        .order_by(SalesPipelineStage.position.asc())
        .all()
    )
    stage_by_code = {s.code: s for s in stages}
    summary["pipeline_id"] = pipeline.id
    summary["stages"] = list(stage_by_code.keys())

    company_specs = [
        ("Acme Démo SA", "Paris", "75001"),
        ("Nordic Soft DEMO", "Lille", "59000"),
        ("Atlas Retail DEMO", "Lyon", "69002"),
        ("Horizon SaaS DEMO", "Nantes", "44000"),
        ("Pixel Labs DEMO", "Bordeaux", "33000"),
    ]
    companies = []
    for i, (name, city, postal) in enumerate(company_specs):
        companies.append(
            create_company(
                db,
                organization_id=org_id,
                user_id=uid,
                data={
                    "name": name,
                    "email": f"contact{i + 1}@demo.salespilot.local",
                    "city": city,
                    "postal_code": postal,
                    "country": "FR",
                    "source": DEMO_SOURCE,
                    "owner_user_id": uid,
                    "notes_preview": DEMO_MARKER,
                    "industry": "Services",
                },
            )
        )
    summary["companies"] = len(companies)

    people = []
    first_names = ["Alice", "Bruno", "Chloé", "David", "Emma", "Farid", "Gina", "Hugo", "Inès", "Jules"]
    for i, fn in enumerate(first_names):
        company = companies[i % len(companies)]
        people.append(
            create_person(
                db,
                organization_id=org_id,
                user_id=uid,
                data={
                    "first_name": fn,
                    "last_name": "Demo",
                    "email": f"{fn.lower()}.demo@demo.salespilot.local",
                    "company_id": company.id,
                    "job_title": "Décideur",
                    "owner_user_id": uid,
                },
            )
        )
    summary["contacts"] = len(people)

    leads = []
    for i in range(8):
        leads.append(
            create_lead(
                db,
                organization_id=org_id,
                user_id=uid,
                data={
                    "title": f"{DEMO_MARKER} Prospect {i + 1}",
                    "status": ["new", "contacted", "qualified", "new"][i % 4],
                    "source": DEMO_SOURCE,
                    "priority": ["low", "medium", "high"][i % 3],
                    "company_name": companies[i % len(companies)].name,
                    "contact_name": f"{people[i].first_name} Demo",
                    "email": people[i].email,
                    "estimated_amount": Decimal(str(5000 + i * 1500)),
                    "owner_user_id": uid,
                    "company_id": companies[i % len(companies)].id,
                    "person_id": people[i].id,
                    "description": f"{DEMO_MARKER} lead seed",
                },
            )
        )
    summary["leads"] = len(leads)

    # 12 opportunities across non-terminal + one won/lost
    open_stages = [s for s in stages if not s.is_won and not s.is_lost]
    opps = []
    for i in range(12):
        if i == 10 and "gagne" in stage_by_code:
            stage = stage_by_code["gagne"]
            status = "won"
        elif i == 11 and "perdu" in stage_by_code:
            stage = stage_by_code["perdu"]
            status = "lost"
        else:
            stage = open_stages[i % len(open_stages)]
            status = "open"
        company = companies[i % len(companies)]
        person = people[i % len(people)]
        opp = create_opportunity(
            db,
            organization_id=org_id,
            user_id=uid,
            data={
                "name": f"{DEMO_MARKER} Opportunité {i + 1}",
                "estimated_amount": Decimal(str(8000 + i * 2200)),
                "pipeline_id": pipeline.id,
                "stage_id": stage.id,
                "company_id": company.id,
                "person_id": person.id,
                "owner_user_id": uid,
                "source": DEMO_SOURCE,
                "priority": ["low", "medium", "high"][i % 3],
                "status": status,
                "expected_close_date": date.today() + timedelta(days=14 + i * 3),
                "description": f"{DEMO_MARKER} deal seed",
                "lead_id": leads[i % len(leads)].id if i < 8 else None,
            },
        )
        # Age some deals for intelligence
        if i in (0, 1, 2):
            opp.stage_entered_at = _now() - timedelta(days=25 + i * 5)
            opp.updated_at = _now() - timedelta(days=20)
        add_product(
            db,
            organization_id=org_id,
            user_id=uid,
            opportunity_id=opp.id,
            data={
                "name": f"Prestation DEMO {i + 1}",
                "quantity": "1",
                "unit_price": str(8000 + i * 2200),
                "discount_percent": "0",
                "position": 0,
            },
        )
        add_participant(
            db,
            organization_id=org_id,
            user_id=uid,
            opportunity_id=opp.id,
            data={"person_id": person.id, "role": "decision_maker", "is_primary": True},
        )
        opps.append(opp)
    summary["opportunities"] = len(opps)

    # Activities past & future
    for i in range(10):
        create_activity(
            db,
            organization_id=org_id,
            user_id=uid,
            data={
                "activity_type": ["call", "email", "meeting", "visit"][i % 4],
                "subject": f"{DEMO_MARKER} Activité {i + 1}",
                "activity_at": _now() + timedelta(days=i - 5),
                "owner_user_id": uid,
                "comment": DEMO_MARKER,
                "opportunity_id": opps[i % len(opps)].id,
                "company_id": companies[i % len(companies)].id,
                "person_id": people[i % len(people)].id,
            },
        )
    summary["activities"] = 10

    # Tasks normal + overdue critical
    for i in range(8):
        overdue = i < 3
        create_task(
            db,
            organization_id=org_id,
            user_id=uid,
            data={
                "title": f"{DEMO_MARKER} Tâche {'critique ' if overdue else ''}{i + 1}",
                "description": DEMO_MARKER,
                "due_at": _now() - timedelta(days=2 + i) if overdue else _now() + timedelta(days=3 + i),
                "priority": "high" if overdue else ["low", "medium", "high"][i % 3],
                "status": "todo",
                "assignee_user_id": uid,
                "opportunity_id": opps[i % len(opps)].id,
            },
        )
    summary["tasks"] = 8

    for i, opp in enumerate(opps[:5]):
        create_note(
            db,
            organization_id=org_id,
            user_id=uid,
            data={
                "body_markdown": f"{DEMO_MARKER} Note contextuelle #{i + 1}",
                "entity_type": "opportunity",
                "entity_id": opp.id,
            },
        )
    summary["notes"] = 5

    # Proposals: draft, sent, accepted (ready to convert) — status forcé DEMO
    prop_svc = ProposalService(db)
    proposal_ids: list[int] = []
    for title, target, opp_i in (
        ("Proposition brouillon", "draft", 3),
        ("Proposition envoyée", "sent", 4),
        ("Proposition acceptée", "accepted", 5),
    ):
        opp = opps[opp_i]
        prop = prop_svc.create_proposal(
            organization_id=org_id,
            user_id=uid,
            data=ProposalCreate(
                opportunity_id=opp.id,
                title=f"{DEMO_MARKER} {title}",
                currency="EUR",
                valid_until=date.today() + timedelta(days=7 if target == "accepted" else 30),
                seed_from_opportunity_products=True,
            ),
        )
        version = prop_svc._get_current_version(prop)
        version.introduction = DEMO_MARKER
        version.payment_terms = "30 jours net"
        version.terms = "CGV"
        prop_svc._recompute_version_totals(version)
        prop_svc._refresh_readiness(prop, version)
        if target == "sent":
            prop.status = ProposalStatus.sent.value
            if hasattr(prop, "sent_at"):
                prop.sent_at = _now()
        elif target == "accepted":
            prop.status = ProposalStatus.accepted.value
            if hasattr(prop, "accepted_at"):
                prop.accepted_at = _now()
            version.valid_until = date.today() + timedelta(days=2)
        proposal_ids.append(prop.id)
    summary["proposals"] = proposal_ids

    collab = SalesCollaborationService(db)
    team = collab.create_team(
        organization_id=org_id,
        user_id=uid,
        data=TeamCreate(
            name="Équipe commerciale DEMO",
            description=f"{DEMO_MARKER} équipe seed",
            lead_user_id=uid,
        ),
    )
    try:
        collab.add_member(
            organization_id=org_id,
            user_id=uid,
            team_id=team.id,
            data=TeamMemberIn(user_id=uid, role="lead"),
        )
    except Exception:
        pass
    summary["team_id"] = team.id

    mention_label = (getattr(user, "first_name", None) or "User").strip() or "User"
    comment = collab.create_comment(
        organization_id=org_id,
        user_id=uid,
        data=CommentCreate(
            entity_type="opportunity",
            entity_id=opps[0].id,
            body=f"{DEMO_MARKER} Commentaire avec mention @[{uid}:{mention_label}]",
        ),
    )
    summary["comment_id"] = comment.id

    follower = collab.follow(
        organization_id=org_id,
        user_id=uid,
        data=FollowIn(entity_type="opportunity", entity_id=opps[1].id),
    )
    summary["follower_id"] = getattr(follower, "id", None)

    review = collab.create_review(
        organization_id=org_id,
        user_id=uid,
        data=ReviewCreate(
            entity_type="opportunity",
            entity_id=opps[2].id,
            reviewer_user_id=uid,
            message=f"{DEMO_MARKER} Revue demandée",
        ),
    )
    summary["review_id"] = getattr(review, "id", None)

    # Insights via rules engine sync (best-effort — Decision Center schema may lag)
    try:
        intel = SalesIntelligenceService(db)
        sync_out = intel.sync(organization_id=org_id, user_id=uid)
        summary["insights_sync"] = {
            "created": getattr(sync_out, "created", None),
            "updated": getattr(sync_out, "updated", None),
            "resolved": getattr(sync_out, "resolved", None),
        }
    except Exception as exc:  # noqa: BLE001
        summary["insights_sync"] = {"error": str(exc)}
        print(f"WARN intelligence sync: {exc}")

    db.commit()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DEMO SalesPilot")
    parser.add_argument("--organization-id", type=int, default=None)
    parser.add_argument("--purge", action="store_true", help="Supprime le seed DEMO de l'org")
    parser.add_argument("--force", action="store_true", help="Reseed même si déjà présent")
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND))
    from app.config import settings
    from app.database import SessionLocal

    _assert_safe(settings)

    try:
        from app.database import Base, engine, init_db

        import app.sales_crm.models  # noqa: F401
        import app.sales_proposals.models  # noqa: F401
        import app.sales_intelligence.models  # noqa: F401
        import app.sales_operations.models  # noqa: F401
        import app.sales_collaboration.models  # noqa: F401

        try:
            init_db()
        except Exception:
            Base.metadata.create_all(bind=engine)
            from app.database import _sqlite_add_column_if_missing

            _sqlite_add_column_if_missing(
                "sales_companies", "linked_customer_id", "linked_customer_id INTEGER"
            )
    except Exception as exc:  # noqa: BLE001
        print(f"WARN schema: {exc}")

    db = SessionLocal()
    try:
        org, user = _resolve_org(db, args.organization_id)
        print(f"Org={org.id} ({org.name}) user={user.id} ({user.email})")

        if args.purge:
            counts = purge_demo(db, org.id)
            print("PURGE DEMO:", counts)
            return 0

        if _already_seeded(db, org.id) and not args.force:
            print("IDEMPOTENT: seed DEMO déjà présent (≥8 leads). Utilisez --force ou --purge.")
            return 0

        if args.force:
            purge_demo(db, org.id)

        summary = seed(db, org, user)
        print("SEED DEMO OK:")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
