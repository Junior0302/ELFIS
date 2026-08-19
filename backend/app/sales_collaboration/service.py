"""Sales Collaboration Service — teams, assign, comments, followers, reviews, transfer."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_saas import OrganizationMember, User
from app.sales_collaboration.models import (
    SalesComment,
    SalesFollower,
    SalesOwnershipTransfer,
    SalesReviewRequest,
    SalesTeam,
    SalesTeamMember,
)
from app.sales_collaboration.schemas import (
    AssignIn,
    AssignOut,
    CommentCreate,
    CommentOut,
    CommentUpdate,
    FollowIn,
    FollowerOut,
    MentionCandidate,
    ReviewCreate,
    ReviewDecide,
    ReviewOut,
    TeamCreate,
    TeamDashboardOut,
    TeamMemberIn,
    TeamMemberOut,
    TeamOut,
    TeamUpdate,
    TransferIn,
    TransferOut,
)
from app.sales_crm.models import (
    SalesActivity,
    SalesCompany,
    SalesLead,
    SalesOpportunity,
    SalesPerson,
    SalesTask,
)
from app.sales_crm.service import soft_alive
from app.sales_proposals.models import CommercialProposal

_MENTION_RE = re.compile(r"@\[(\d+):([^\]]+)\]")


def _now() -> datetime:
    return datetime.utcnow()


def _user_label(user: User | None) -> str | None:
    if not user:
        return None
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or user.email


class SalesCollaborationService:
    def __init__(self, db: Session):
        self.db = db

    # ----- helpers -----

    def _get_user(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, detail={"code": "user_not_found", "message": "Utilisateur introuvable"})
        return user

    def _assert_org_member(self, organization_id: int, user_id: int) -> None:
        row = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
            )
            .first()
        )
        if not row:
            raise HTTPException(
                400,
                detail={"code": "not_org_member", "message": "Utilisateur hors organisation"},
            )

    def _route(self, entity_type: str, entity_id: int) -> str:
        mapping = {
            "lead": f"/sales/workspace/lead/{entity_id}",
            "company": f"/sales/workspace/company/{entity_id}",
            "person": f"/sales/workspace/person/{entity_id}",
            "opportunity": f"/sales/deals/{entity_id}",
            "proposal": f"/sales/proposals/{entity_id}",
            "activity": "/sales/activities",
            "task": "/sales/tasks",
            "workspace": f"/sales/workspace/opportunity/{entity_id}",
        }
        return mapping.get(entity_type, "/sales")

    def _publish(
        self,
        *,
        event_name: str,
        organization_id: int,
        aggregate_type: str,
        aggregate_id: int | str,
        payload: dict[str, Any],
        actor_user_id: int | None,
        idempotency_key: str,
    ) -> None:
        safe_publish(
            self.db,
            DomainEvent(
                event_name=event_name,
                organization_id=organization_id,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                payload=payload,
                metadata={"actor_user_id": str(actor_user_id) if actor_user_id else None},
                idempotency_key=idempotency_key,
            ),
            commit=False,
        )

    def _notify(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        title: str,
        message: str,
        action_url: str,
        idempotency_key: str,
        notification_type: str = "sales_collab",
        severity: str = "info",
    ) -> None:
        if not user_id:
            return
        try:
            from app.notifications.notification_schemas import NotificationRequest
            from app.notifications.notification_service import NotificationService

            NotificationService(self.db).create_notification(
                NotificationRequest(
                    organization_id=organization_id,
                    user_id=user_id,
                    notification_type=notification_type,
                    category="sales",
                    severity=severity,
                    template_name="system_generic",
                    template_data={"title": title, "message": message[:200]},
                    channels=["in_app"],
                    action_url=action_url,
                    action_label="Ouvrir",
                    related_entity_type="sales_collab",
                    related_entity_id=idempotency_key,
                    idempotency_key=idempotency_key,
                )
            )
        except Exception:
            return

    def _notify_followers(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        exclude_user_id: int | None,
        title: str,
        message: str,
        event_key: str,
    ) -> None:
        followers = (
            self.db.query(SalesFollower)
            .filter(
                SalesFollower.organization_id == organization_id,
                SalesFollower.entity_type == entity_type,
                SalesFollower.entity_id == entity_id,
                SalesFollower.deleted_at.is_(None),
            )
            .all()
        )
        route = self._route(entity_type, entity_id)
        for f in followers:
            if exclude_user_id and f.user_id == exclude_user_id:
                continue
            self._notify(
                organization_id=organization_id,
                user_id=f.user_id,
                title=title,
                message=message,
                action_url=route,
                idempotency_key=f"sales:collab:follow:{event_key}:{f.user_id}",
            )

    def _resolve_row(self, organization_id: int, entity_type: str, entity_id: int) -> Any:
        model_map = {
            "lead": SalesLead,
            "company": SalesCompany,
            "person": SalesPerson,
            "opportunity": SalesOpportunity,
            "activity": SalesActivity,
            "task": SalesTask,
            "proposal": CommercialProposal,
            "workspace": SalesOpportunity,
        }
        model = model_map.get(entity_type)
        if not model:
            raise HTTPException(400, detail={"code": "invalid_entity", "message": "Type invalide"})
        if entity_type == "proposal":
            row = (
                self.db.query(CommercialProposal)
                .filter(
                    CommercialProposal.organization_id == organization_id,
                    CommercialProposal.id == entity_id,
                    CommercialProposal.deleted_at.is_(None),
                )
                .first()
            )
        else:
            row = soft_alive(self.db.query(model), model).filter(
                model.organization_id == organization_id,
                model.id == entity_id,
            ).first()
        if not row:
            raise HTTPException(404, detail={"code": "not_found", "message": "Ressource introuvable"})
        return row

    def _get_owner(self, row: Any, entity_type: str) -> int | None:
        if entity_type == "task":
            return getattr(row, "assignee_user_id", None)
        return getattr(row, "owner_user_id", None)

    def _set_owner(self, row: Any, entity_type: str, owner_user_id: int) -> None:
        if entity_type == "task":
            row.assignee_user_id = owner_user_id
        else:
            row.owner_user_id = owner_user_id
        if hasattr(row, "updated_at"):
            row.updated_at = _now()

    # ----- Teams -----

    def list_teams(self, *, organization_id: int) -> list[TeamOut]:
        rows = (
            self.db.query(SalesTeam)
            .filter(
                SalesTeam.organization_id == organization_id,
                SalesTeam.deleted_at.is_(None),
            )
            .order_by(SalesTeam.name.asc())
            .all()
        )
        return [self._team_out(t) for t in rows]

    def create_team(
        self, *, organization_id: int, user_id: int | None, data: TeamCreate
    ) -> TeamOut:
        if data.lead_user_id:
            self._assert_org_member(organization_id, data.lead_user_id)
        team = SalesTeam(
            organization_id=organization_id,
            name=data.name.strip(),
            description=data.description,
            lead_user_id=data.lead_user_id,
            created_by=user_id,
            status="active",
        )
        self.db.add(team)
        self.db.flush()
        if data.lead_user_id:
            self.db.add(
                SalesTeamMember(
                    organization_id=organization_id,
                    team_id=team.id,
                    user_id=data.lead_user_id,
                    role="lead",
                    sort_order=0,
                    status="active",
                )
            )
            self.db.flush()
        self._publish(
            event_name=EventNames.SALES_TEAM_CREATED,
            organization_id=organization_id,
            aggregate_type="sales_team",
            aggregate_id=team.id,
            payload={"team_id": team.id, "name": team.name},
            actor_user_id=user_id,
            idempotency_key=f"sales:team:created:{organization_id}:{team.id}",
        )
        return self._team_out(team)

    def update_team(
        self, *, organization_id: int, user_id: int | None, team_id: int, data: TeamUpdate
    ) -> TeamOut:
        team = self._get_team(organization_id, team_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(team, key, value)
        team.updated_at = _now()
        self.db.flush()
        self._publish(
            event_name=EventNames.SALES_TEAM_UPDATED,
            organization_id=organization_id,
            aggregate_type="sales_team",
            aggregate_id=team.id,
            payload={"team_id": team.id},
            actor_user_id=user_id,
            idempotency_key=f"sales:team:updated:{team.id}:{int(_now().timestamp())}",
        )
        return self._team_out(team)

    def add_member(
        self, *, organization_id: int, user_id: int | None, team_id: int, data: TeamMemberIn
    ) -> TeamMemberOut:
        team = self._get_team(organization_id, team_id)
        self._assert_org_member(organization_id, data.user_id)
        existing = (
            self.db.query(SalesTeamMember)
            .filter(
                SalesTeamMember.team_id == team.id,
                SalesTeamMember.user_id == data.user_id,
                SalesTeamMember.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            existing.role = data.role
            existing.permissions = data.permissions or {}
            existing.sort_order = data.sort_order
            existing.status = "active"
            member = existing
        else:
            member = SalesTeamMember(
                organization_id=organization_id,
                team_id=team.id,
                user_id=data.user_id,
                role=data.role,
                permissions=data.permissions or {},
                sort_order=data.sort_order,
                status="active",
            )
            self.db.add(member)
        self.db.flush()
        self._publish(
            event_name=EventNames.SALES_TEAM_MEMBER_ADDED,
            organization_id=organization_id,
            aggregate_type="sales_team",
            aggregate_id=team.id,
            payload={"team_id": team.id, "user_id": data.user_id, "role": data.role},
            actor_user_id=user_id,
            idempotency_key=f"sales:team:member:{team.id}:{data.user_id}",
        )
        return self._member_out(member)

    def remove_member(
        self, *, organization_id: int, user_id: int | None, team_id: int, member_user_id: int
    ) -> None:
        team = self._get_team(organization_id, team_id)
        member = (
            self.db.query(SalesTeamMember)
            .filter(
                SalesTeamMember.team_id == team.id,
                SalesTeamMember.user_id == member_user_id,
                SalesTeamMember.deleted_at.is_(None),
            )
            .first()
        )
        if not member:
            raise HTTPException(404, detail={"code": "not_found", "message": "Membre introuvable"})
        member.deleted_at = _now()
        member.status = "removed"
        self.db.flush()

    def _get_team(self, organization_id: int, team_id: int) -> SalesTeam:
        team = (
            self.db.query(SalesTeam)
            .filter(
                SalesTeam.id == team_id,
                SalesTeam.organization_id == organization_id,
                SalesTeam.deleted_at.is_(None),
            )
            .first()
        )
        if not team:
            raise HTTPException(404, detail={"code": "not_found", "message": "Équipe introuvable"})
        return team

    def _team_out(self, team: SalesTeam) -> TeamOut:
        members = (
            self.db.query(SalesTeamMember)
            .filter(
                SalesTeamMember.team_id == team.id,
                SalesTeamMember.deleted_at.is_(None),
            )
            .order_by(SalesTeamMember.sort_order.asc(), SalesTeamMember.id.asc())
            .all()
        )
        return TeamOut(
            id=team.id,
            name=team.name,
            description=team.description,
            lead_user_id=team.lead_user_id,
            status=team.status,
            created_at=team.created_at,
            updated_at=team.updated_at,
            members=[self._member_out(m) for m in members],
        )

    def _member_out(self, member: SalesTeamMember) -> TeamMemberOut:
        user = self.db.query(User).filter(User.id == member.user_id).first()
        return TeamMemberOut(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            role=member.role,
            permissions=member.permissions or {},
            sort_order=member.sort_order,
            status=member.status,
            user_label=_user_label(user),
        )

    def team_member_ids(self, organization_id: int, team_id: int | None) -> list[int]:
        q = self.db.query(SalesTeamMember.user_id).filter(
            SalesTeamMember.organization_id == organization_id,
            SalesTeamMember.deleted_at.is_(None),
            SalesTeamMember.status == "active",
        )
        if team_id:
            q = q.filter(SalesTeamMember.team_id == team_id)
        return [r[0] for r in q.distinct().all()]

    # ----- Assign -----

    def assign(self, *, organization_id: int, user_id: int | None, data: AssignIn) -> AssignOut:
        self._assert_org_member(organization_id, data.owner_user_id)
        entity_type = data.resource
        row = self._resolve_row(organization_id, entity_type, data.resource_id)
        previous = self._get_owner(row, entity_type)
        if previous == data.owner_user_id:
            return AssignOut(
                resource=entity_type,
                resource_id=data.resource_id,
                previous_owner_user_id=previous,
                owner_user_id=data.owner_user_id,
                assigned_at=_now(),
            )
        self._set_owner(row, entity_type, data.owner_user_id)
        self.db.flush()
        route = self._route(entity_type, data.resource_id)
        self._publish(
            event_name=EventNames.SALES_ASSIGNMENT_CHANGED,
            organization_id=organization_id,
            aggregate_type=f"sales_{entity_type}",
            aggregate_id=data.resource_id,
            payload={
                "resource": entity_type,
                "resource_id": data.resource_id,
                "previous_owner_user_id": previous,
                "owner_user_id": data.owner_user_id,
                "comment": data.comment,
            },
            actor_user_id=user_id,
            idempotency_key=f"sales:assign:{entity_type}:{data.resource_id}:{data.owner_user_id}:{int(_now().timestamp())}",
        )
        if data.owner_user_id != user_id:
            self._notify(
                organization_id=organization_id,
                user_id=data.owner_user_id,
                title="Assignation",
                message=f"Une ressource {entity_type} vous a été assignée.",
                action_url=route,
                idempotency_key=f"sales:collab:assign:{entity_type}:{data.resource_id}:{data.owner_user_id}",
                notification_type="sales_assignment",
            )
        self._notify_followers(
            organization_id=organization_id,
            entity_type=entity_type if entity_type != "workspace" else "opportunity",
            entity_id=data.resource_id,
            exclude_user_id=user_id,
            title="Assignation",
            message=f"Changement de propriétaire ({entity_type}).",
            event_key=f"assign:{entity_type}:{data.resource_id}:{data.owner_user_id}",
        )
        return AssignOut(
            resource=entity_type,
            resource_id=data.resource_id,
            previous_owner_user_id=previous,
            owner_user_id=data.owner_user_id,
            assigned_at=_now(),
        )

    # ----- Comments & mentions -----

    def parse_mentions(self, organization_id: int, body: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        seen: set[int] = set()
        for match in _MENTION_RE.finditer(body):
            uid = int(match.group(1))
            label = match.group(2).strip()
            if uid in seen:
                continue
            try:
                self._assert_org_member(organization_id, uid)
            except HTTPException:
                continue
            seen.add(uid)
            found.append({"user_id": uid, "label": label})
        return found

    def mention_candidates(
        self, *, organization_id: int, q: str = "", limit: int = 20
    ) -> list[MentionCandidate]:
        members = (
            self.db.query(User)
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.status == "active",
            )
            .limit(100)
            .all()
        )
        qn = (q or "").strip().lower()
        out: list[MentionCandidate] = []
        for u in members:
            label = _user_label(u) or u.email or str(u.id)
            if qn and qn not in label.lower() and qn not in (u.email or "").lower():
                continue
            out.append(MentionCandidate(user_id=u.id, label=label, email=u.email))
            if len(out) >= limit:
                break
        return out

    def list_comments(
        self, *, organization_id: int, entity_type: str, entity_id: int
    ) -> list[CommentOut]:
        rows = (
            self.db.query(SalesComment)
            .filter(
                SalesComment.organization_id == organization_id,
                SalesComment.entity_type == entity_type,
                SalesComment.entity_id == entity_id,
                SalesComment.deleted_at.is_(None),
            )
            .order_by(SalesComment.created_at.asc())
            .limit(200)
            .all()
        )
        return [self._comment_out(r) for r in rows]

    def create_comment(
        self, *, organization_id: int, user_id: int | None, data: CommentCreate
    ) -> CommentOut:
        self._resolve_row(organization_id, data.entity_type, data.entity_id)
        mentions = self.parse_mentions(organization_id, data.body)
        row = SalesComment(
            organization_id=organization_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            author_user_id=user_id,
            body=data.body.strip(),
            mentions=mentions,
            vault_document_ids=data.vault_document_ids or [],
        )
        self.db.add(row)
        self.db.flush()
        route = self._route(data.entity_type, data.entity_id)
        self._publish(
            event_name=EventNames.SALES_COMMENT_CREATED,
            organization_id=organization_id,
            aggregate_type="sales_comment",
            aggregate_id=row.id,
            payload={
                "comment_id": row.id,
                "entity_type": data.entity_type,
                "entity_id": data.entity_id,
                "mentions": mentions,
            },
            actor_user_id=user_id,
            idempotency_key=f"sales:comment:created:{row.id}",
        )
        for m in mentions:
            if m["user_id"] == user_id:
                continue
            self._publish(
                event_name=EventNames.SALES_MENTION_CREATED,
                organization_id=organization_id,
                aggregate_type="sales_comment",
                aggregate_id=row.id,
                payload={"mentioned_user_id": m["user_id"], "comment_id": row.id},
                actor_user_id=user_id,
                idempotency_key=f"sales:mention:{row.id}:{m['user_id']}",
            )
            self._notify(
                organization_id=organization_id,
                user_id=m["user_id"],
                title="Mention",
                message=f"Vous avez été mentionné·e : {data.body[:80]}",
                action_url=route,
                idempotency_key=f"sales:collab:mention:{row.id}:{m['user_id']}",
                notification_type="sales_mention",
            )
        self._notify_followers(
            organization_id=organization_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            exclude_user_id=user_id,
            title="Nouveau commentaire",
            message=data.body[:100],
            event_key=f"comment:{row.id}",
        )
        return self._comment_out(row)

    def update_comment(
        self, *, organization_id: int, user_id: int | None, comment_id: int, data: CommentUpdate
    ) -> CommentOut:
        row = (
            self.db.query(SalesComment)
            .filter(
                SalesComment.id == comment_id,
                SalesComment.organization_id == organization_id,
                SalesComment.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(404, detail={"code": "not_found", "message": "Commentaire introuvable"})
        if row.author_user_id and user_id and row.author_user_id != user_id:
            raise HTTPException(403, detail={"code": "forbidden", "message": "Auteur uniquement"})
        row.body = data.body.strip()
        row.mentions = self.parse_mentions(organization_id, data.body)
        if data.vault_document_ids is not None:
            row.vault_document_ids = data.vault_document_ids
        row.edited_at = _now()
        row.updated_at = _now()
        self.db.flush()
        self._publish(
            event_name=EventNames.SALES_COMMENT_UPDATED,
            organization_id=organization_id,
            aggregate_type="sales_comment",
            aggregate_id=row.id,
            payload={"comment_id": row.id},
            actor_user_id=user_id,
            idempotency_key=f"sales:comment:updated:{row.id}:{int(_now().timestamp())}",
        )
        return self._comment_out(row)

    def delete_comment(
        self, *, organization_id: int, user_id: int | None, comment_id: int
    ) -> None:
        row = (
            self.db.query(SalesComment)
            .filter(
                SalesComment.id == comment_id,
                SalesComment.organization_id == organization_id,
                SalesComment.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(404, detail={"code": "not_found", "message": "Commentaire introuvable"})
        row.deleted_at = _now()
        self.db.flush()
        self._publish(
            event_name=EventNames.SALES_COMMENT_DELETED,
            organization_id=organization_id,
            aggregate_type="sales_comment",
            aggregate_id=row.id,
            payload={"comment_id": row.id},
            actor_user_id=user_id,
            idempotency_key=f"sales:comment:deleted:{row.id}",
        )

    def _comment_out(self, row: SalesComment) -> CommentOut:
        author = self.db.query(User).filter(User.id == row.author_user_id).first() if row.author_user_id else None
        return CommentOut(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            author_user_id=row.author_user_id,
            author_label=_user_label(author),
            body=row.body,
            mentions=row.mentions or [],
            vault_document_ids=row.vault_document_ids or [],
            edited_at=row.edited_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # ----- Followers -----

    def list_followers(
        self, *, organization_id: int, entity_type: str, entity_id: int
    ) -> list[FollowerOut]:
        rows = (
            self.db.query(SalesFollower)
            .filter(
                SalesFollower.organization_id == organization_id,
                SalesFollower.entity_type == entity_type,
                SalesFollower.entity_id == entity_id,
                SalesFollower.deleted_at.is_(None),
            )
            .order_by(SalesFollower.created_at.asc())
            .all()
        )
        out: list[FollowerOut] = []
        for r in rows:
            user = self.db.query(User).filter(User.id == r.user_id).first()
            out.append(
                FollowerOut(
                    id=r.id,
                    entity_type=r.entity_type,
                    entity_id=r.entity_id,
                    user_id=r.user_id,
                    user_label=_user_label(user),
                    created_at=r.created_at,
                )
            )
        return out

    def follow(
        self, *, organization_id: int, user_id: int, data: FollowIn
    ) -> FollowerOut:
        self._resolve_row(organization_id, data.entity_type, data.entity_id)
        existing = (
            self.db.query(SalesFollower)
            .filter(
                SalesFollower.organization_id == organization_id,
                SalesFollower.entity_type == data.entity_type,
                SalesFollower.entity_id == data.entity_id,
                SalesFollower.user_id == user_id,
            )
            .first()
        )
        if existing and not existing.deleted_at:
            user = self.db.query(User).filter(User.id == user_id).first()
            return FollowerOut(
                id=existing.id,
                entity_type=existing.entity_type,
                entity_id=existing.entity_id,
                user_id=existing.user_id,
                user_label=_user_label(user),
                created_at=existing.created_at,
            )
        if existing:
            existing.deleted_at = None
            existing.created_at = _now()
            row = existing
        else:
            row = SalesFollower(
                organization_id=organization_id,
                entity_type=data.entity_type,
                entity_id=data.entity_id,
                user_id=user_id,
            )
            self.db.add(row)
        self.db.flush()
        user = self.db.query(User).filter(User.id == user_id).first()
        return FollowerOut(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            user_id=row.user_id,
            user_label=_user_label(user),
            created_at=row.created_at,
        )

    def unfollow(
        self, *, organization_id: int, user_id: int, entity_type: str, entity_id: int
    ) -> None:
        row = (
            self.db.query(SalesFollower)
            .filter(
                SalesFollower.organization_id == organization_id,
                SalesFollower.entity_type == entity_type,
                SalesFollower.entity_id == entity_id,
                SalesFollower.user_id == user_id,
                SalesFollower.deleted_at.is_(None),
            )
            .first()
        )
        if row:
            row.deleted_at = _now()
            self.db.flush()

    # ----- Reviews -----

    def create_review(
        self, *, organization_id: int, user_id: int | None, data: ReviewCreate
    ) -> ReviewOut:
        self._assert_org_member(organization_id, data.reviewer_user_id)
        self._resolve_row(organization_id, data.entity_type, data.entity_id)
        row = SalesReviewRequest(
            organization_id=organization_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            requester_user_id=user_id,
            reviewer_user_id=data.reviewer_user_id,
            status="pending",
            message=data.message,
        )
        self.db.add(row)
        self.db.flush()
        route = self._route(data.entity_type, data.entity_id)
        self._publish(
            event_name=EventNames.SALES_REVIEW_REQUESTED,
            organization_id=organization_id,
            aggregate_type="sales_review",
            aggregate_id=row.id,
            payload={
                "review_id": row.id,
                "entity_type": data.entity_type,
                "entity_id": data.entity_id,
                "reviewer_user_id": data.reviewer_user_id,
            },
            actor_user_id=user_id,
            idempotency_key=f"sales:review:req:{row.id}",
        )
        self._notify(
            organization_id=organization_id,
            user_id=data.reviewer_user_id,
            title="Revue demandée",
            message=data.message or f"Revue {data.entity_type} #{data.entity_id}",
            action_url=route,
            idempotency_key=f"sales:collab:review:{row.id}",
            notification_type="sales_review",
            severity="warning",
        )
        return self._review_out(row)

    def decide_review(
        self, *, organization_id: int, user_id: int | None, review_id: int, data: ReviewDecide
    ) -> ReviewOut:
        row = (
            self.db.query(SalesReviewRequest)
            .filter(
                SalesReviewRequest.id == review_id,
                SalesReviewRequest.organization_id == organization_id,
                SalesReviewRequest.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(404, detail={"code": "not_found", "message": "Revue introuvable"})
        if user_id and row.reviewer_user_id != user_id:
            raise HTTPException(403, detail={"code": "forbidden", "message": "Reviewer uniquement"})
        if row.status != "pending":
            raise HTTPException(400, detail={"code": "already_decided", "message": "Déjà décidée"})
        row.status = data.decision
        row.decision_comment = data.decision_comment
        row.decided_at = _now()
        row.updated_at = _now()
        self.db.flush()
        event = {
            "approved": EventNames.SALES_REVIEW_APPROVED,
            "changes_requested": EventNames.SALES_REVIEW_CHANGES_REQUESTED,
            "rejected": EventNames.SALES_REVIEW_REJECTED,
        }[data.decision]
        self._publish(
            event_name=event,
            organization_id=organization_id,
            aggregate_type="sales_review",
            aggregate_id=row.id,
            payload={"review_id": row.id, "decision": data.decision},
            actor_user_id=user_id,
            idempotency_key=f"sales:review:decide:{row.id}:{data.decision}",
        )
        route = self._route(row.entity_type, row.entity_id)
        if row.requester_user_id and row.requester_user_id != user_id:
            self._notify(
                organization_id=organization_id,
                user_id=row.requester_user_id,
                title="Revue décidée",
                message=f"Statut : {data.decision}",
                action_url=route,
                idempotency_key=f"sales:collab:review:dec:{row.id}",
                notification_type="sales_review",
            )
        self._notify_followers(
            organization_id=organization_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            exclude_user_id=user_id,
            title="Revue",
            message=f"Revue {data.decision}",
            event_key=f"review:{row.id}:{data.decision}",
        )
        return self._review_out(row)

    def list_reviews(
        self,
        *,
        organization_id: int,
        user_id: int | None = None,
        status: str | None = "pending",
        for_reviewer: bool = False,
    ) -> list[ReviewOut]:
        q = self.db.query(SalesReviewRequest).filter(
            SalesReviewRequest.organization_id == organization_id,
            SalesReviewRequest.deleted_at.is_(None),
        )
        if status:
            q = q.filter(SalesReviewRequest.status == status)
        if for_reviewer and user_id:
            q = q.filter(SalesReviewRequest.reviewer_user_id == user_id)
        rows = q.order_by(SalesReviewRequest.created_at.desc()).limit(100).all()
        return [self._review_out(r) for r in rows]

    def _review_out(self, row: SalesReviewRequest) -> ReviewOut:
        return ReviewOut(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            requester_user_id=row.requester_user_id,
            reviewer_user_id=row.reviewer_user_id,
            status=row.status,
            message=row.message,
            decision_comment=row.decision_comment,
            decided_at=row.decided_at,
            created_at=row.created_at,
            route=self._route(row.entity_type, row.entity_id),
        )

    # ----- Transfer -----

    def transfer(
        self, *, organization_id: int, user_id: int | None, data: TransferIn
    ) -> TransferOut:
        self._assert_org_member(organization_id, data.to_user_id)
        row = self._resolve_row(organization_id, data.entity_type, data.entity_id)
        from_id = self._get_owner(row, data.entity_type)
        self._set_owner(row, data.entity_type, data.to_user_id)
        transfer = SalesOwnershipTransfer(
            organization_id=organization_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            from_user_id=from_id,
            to_user_id=data.to_user_id,
            reason=data.reason.strip(),
            comment=data.comment,
            initiated_by=user_id,
        )
        self.db.add(transfer)
        self.db.flush()
        route = self._route(data.entity_type, data.entity_id)
        self._publish(
            event_name=EventNames.SALES_TRANSFER_COMPLETED,
            organization_id=organization_id,
            aggregate_type=f"sales_{data.entity_type}",
            aggregate_id=data.entity_id,
            payload={
                "transfer_id": transfer.id,
                "from_user_id": from_id,
                "to_user_id": data.to_user_id,
                "reason": data.reason,
            },
            actor_user_id=user_id,
            idempotency_key=f"sales:transfer:{transfer.id}",
        )
        self._notify(
            organization_id=organization_id,
            user_id=data.to_user_id,
            title="Transfert de propriété",
            message=f"Motif : {data.reason}",
            action_url=route,
            idempotency_key=f"sales:collab:transfer:{transfer.id}:to",
            notification_type="sales_transfer",
            severity="warning",
        )
        if from_id and from_id != data.to_user_id and from_id != user_id:
            self._notify(
                organization_id=organization_id,
                user_id=from_id,
                title="Propriété transférée",
                message=f"Motif : {data.reason}",
                action_url=route,
                idempotency_key=f"sales:collab:transfer:{transfer.id}:from",
                notification_type="sales_transfer",
            )
        self._notify_followers(
            organization_id=organization_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            exclude_user_id=user_id,
            title="Transfert",
            message=f"Propriété transférée ({data.reason})",
            event_key=f"transfer:{transfer.id}",
        )
        return TransferOut(
            id=transfer.id,
            entity_type=transfer.entity_type,
            entity_id=transfer.entity_id,
            from_user_id=transfer.from_user_id,
            to_user_id=transfer.to_user_id,
            reason=transfer.reason,
            comment=transfer.comment,
            created_at=transfer.created_at,
        )

    # ----- Views -----

    def collab_view(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        view: str,
        resource: str,
        team_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(50, max(1, page_size))
        items: list[dict[str, Any]] = []
        total = 0

        if view == "to_review":
            reviews = self.list_reviews(
                organization_id=organization_id, user_id=user_id, status="pending", for_reviewer=True
            )
            total = len(reviews)
            slice_ = reviews[(page - 1) * page_size : page * page_size]
            items = [r.model_dump(mode="json") for r in slice_]
            return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total}}

        if view == "following":
            follows = (
                self.db.query(SalesFollower)
                .filter(
                    SalesFollower.organization_id == organization_id,
                    SalesFollower.user_id == user_id,
                    SalesFollower.deleted_at.is_(None),
                )
                .order_by(SalesFollower.created_at.desc())
                .all()
            )
            if resource == "opportunities":
                follows = [f for f in follows if f.entity_type in ("opportunity", "workspace")]
            elif resource == "leads":
                follows = [f for f in follows if f.entity_type == "lead"]
            elif resource == "tasks":
                follows = [f for f in follows if f.entity_type == "task"]
            elif resource == "proposals":
                follows = [f for f in follows if f.entity_type == "proposal"]
            elif resource == "activities":
                follows = [f for f in follows if f.entity_type == "activity"]
            total = len(follows)
            for f in follows[(page - 1) * page_size : page * page_size]:
                items.append(
                    {
                        "entity_type": f.entity_type,
                        "entity_id": f.entity_id,
                        "route": self._route(f.entity_type, f.entity_id),
                        "followed_at": f.created_at.isoformat(),
                    }
                )
            return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total}}

        owner_ids: list[int] | None = None
        if view == "mine" or view == "assigned":
            owner_ids = [user_id] if user_id else []
        elif view == "team":
            owner_ids = self.team_member_ids(organization_id, team_id)
            if not owner_ids:
                return {
                    "items": [],
                    "pagination": {"page": page, "page_size": page_size, "total": 0},
                }

        if resource == "leads":
            q = soft_alive(self.db.query(SalesLead), SalesLead).filter(
                SalesLead.organization_id == organization_id
            )
            if owner_ids is not None:
                q = q.filter(SalesLead.owner_user_id.in_(owner_ids))
            total = q.count()
            rows = q.order_by(SalesLead.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
            items = [
                {
                    "id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "owner_user_id": r.owner_user_id,
                    "route": self._route("lead", r.id),
                }
                for r in rows
            ]
        elif resource == "opportunities":
            q = soft_alive(self.db.query(SalesOpportunity), SalesOpportunity).filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == "open",
            )
            if owner_ids is not None:
                q = q.filter(SalesOpportunity.owner_user_id.in_(owner_ids))
            total = q.count()
            rows = (
                q.order_by(SalesOpportunity.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            items = [
                {
                    "id": r.id,
                    "name": r.name,
                    "owner_user_id": r.owner_user_id,
                    "estimated_amount": str(r.estimated_amount) if r.estimated_amount is not None else None,
                    "route": self._route("opportunity", r.id),
                }
                for r in rows
            ]
        elif resource == "tasks":
            q = soft_alive(self.db.query(SalesTask), SalesTask).filter(
                SalesTask.organization_id == organization_id
            )
            if owner_ids is not None:
                q = q.filter(SalesTask.assignee_user_id.in_(owner_ids))
            total = q.count()
            rows = q.order_by(SalesTask.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
            items = [
                {
                    "id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "assignee_user_id": r.assignee_user_id,
                    "due_at": r.due_at.isoformat() if r.due_at else None,
                    "route": self._route("task", r.id),
                }
                for r in rows
            ]
        elif resource == "proposals":
            q = self.db.query(CommercialProposal).filter(
                CommercialProposal.organization_id == organization_id,
                CommercialProposal.deleted_at.is_(None),
            )
            if owner_ids is not None:
                q = q.filter(CommercialProposal.owner_user_id.in_(owner_ids))
            total = q.count()
            rows = (
                q.order_by(CommercialProposal.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            items = [
                {
                    "id": r.id,
                    "proposal_number": r.proposal_number,
                    "status": r.status,
                    "owner_user_id": r.owner_user_id,
                    "route": self._route("proposal", r.id),
                }
                for r in rows
            ]
        else:  # activities
            q = soft_alive(self.db.query(SalesActivity), SalesActivity).filter(
                SalesActivity.organization_id == organization_id
            )
            if owner_ids is not None:
                q = q.filter(SalesActivity.owner_user_id.in_(owner_ids))
            total = q.count()
            rows = (
                q.order_by(SalesActivity.activity_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            items = [
                {
                    "id": r.id,
                    "subject": r.subject,
                    "activity_type": r.activity_type,
                    "owner_user_id": r.owner_user_id,
                    "route": self._route("activity", r.id),
                }
                for r in rows
            ]

        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total}}

    # ----- Team dashboard -----

    def team_dashboard(
        self, *, organization_id: int, team_id: int | None = None
    ) -> TeamDashboardOut:
        team_name = None
        member_ids = self.team_member_ids(organization_id, team_id)
        if team_id:
            team = self._get_team(organization_id, team_id)
            team_name = team.name
            members_out = [m.model_dump() for m in self._team_out(team).members]
        else:
            members_out = []
            if not member_ids:
                # org-wide: all active members with sales activity ownership
                member_ids = [
                    r[0]
                    for r in self.db.query(OrganizationMember.user_id)
                    .filter(
                        OrganizationMember.organization_id == organization_id,
                        OrganizationMember.status == "active",
                    )
                    .all()
                ]

        opp_q = soft_alive(self.db.query(SalesOpportunity), SalesOpportunity).filter(
            SalesOpportunity.organization_id == organization_id,
            SalesOpportunity.status == "open",
        )
        if member_ids:
            opp_q = opp_q.filter(SalesOpportunity.owner_user_id.in_(member_ids))
        opps = opp_q.limit(500).all()
        pipeline_value = float(
            sum((o.estimated_amount or Decimal("0")) for o in opps)
        )

        task_q = soft_alive(self.db.query(SalesTask), SalesTask).filter(
            SalesTask.organization_id == organization_id,
            SalesTask.status != "done",
        )
        if member_ids:
            task_q = task_q.filter(SalesTask.assignee_user_id.in_(member_ids))
        tasks = task_q.limit(500).all()
        now = _now()
        overdue = sum(1 for t in tasks if t.due_at and t.due_at < now)

        reviews_q = self.db.query(SalesReviewRequest).filter(
            SalesReviewRequest.organization_id == organization_id,
            SalesReviewRequest.status == "pending",
            SalesReviewRequest.deleted_at.is_(None),
        )
        if member_ids:
            reviews_q = reviews_q.filter(SalesReviewRequest.reviewer_user_id.in_(member_ids))
        pending_reviews = reviews_q.count()

        load: list[dict[str, Any]] = []
        for uid in member_ids[:50]:
            user = self.db.query(User).filter(User.id == uid).first()
            load.append(
                {
                    "user_id": uid,
                    "label": _user_label(user),
                    "open_opportunities": sum(1 for o in opps if o.owner_user_id == uid),
                    "open_tasks": sum(1 for t in tasks if t.assignee_user_id == uid),
                    "overdue_tasks": sum(
                        1 for t in tasks if t.assignee_user_id == uid and t.due_at and t.due_at < now
                    ),
                }
            )

        insights: list[dict[str, Any]] = []
        if overdue:
            insights.append(
                {
                    "severity": "high",
                    "title": f"{overdue} tâche(s) en retard",
                    "summary": "Charge équipe à rééquilibrer.",
                }
            )
        if pending_reviews:
            insights.append(
                {
                    "severity": "medium",
                    "title": f"{pending_reviews} revue(s) en attente",
                    "summary": "Des validations bloquent le cycle commercial.",
                }
            )

        return TeamDashboardOut(
            team_id=team_id,
            team_name=team_name or "Organisation",
            open_opportunities=len(opps),
            pipeline_value=pipeline_value,
            overdue_tasks=overdue,
            open_tasks=len(tasks),
            pending_reviews=pending_reviews,
            members=members_out,
            load_by_member=load,
            insights=insights,
            generated_at=_now(),
        )
