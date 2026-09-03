"""Sales Collaboration API — /api/sales/collab/*."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.sales_collaboration.permissions import (
    SALES_ASSIGN,
    SALES_COMMENT,
    SALES_MENTION,
    SALES_REVIEW,
    SALES_TEAM_MANAGE,
    SALES_TEAM_READ,
    SALES_TRANSFER,
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
from app.sales_collaboration.service import SalesCollaborationService
from app.sales_crm.permissions import SALES_READ
from app.services.auth import write_audit

router = APIRouter(
    prefix="/sales/collab",
    tags=["sales-collaboration"],
    dependencies=[Depends(require_active_subscription)],
)


def _uid(auth: AuthContext) -> int | None:
    return auth.user.id if auth.user else None


@router.get("/teams", response_model=list[TeamOut])
def list_teams(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require(SALES_TEAM_READ)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).list_teams(organization_id=org_id)


@router.post("/teams", response_model=TeamOut, status_code=201)
def create_team(
    body: TeamCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_TEAM_MANAGE)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).create_team(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    write_audit(db, user_id=_uid(auth), organization_id=org_id, action="sales.team.created", module="sales")
    return out


@router.patch("/teams/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    body: TeamUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_TEAM_MANAGE)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).update_team(
        organization_id=org_id, user_id=_uid(auth), team_id=team_id, data=body
    )
    db.commit()
    return out


@router.post("/teams/{team_id}/members", response_model=TeamMemberOut, status_code=201)
def add_member(
    team_id: int,
    body: TeamMemberIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_TEAM_MANAGE)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).add_member(
        organization_id=org_id, user_id=_uid(auth), team_id=team_id, data=body
    )
    db.commit()
    return out


@router.delete("/teams/{team_id}/members/{member_user_id}", status_code=204)
def remove_member(
    team_id: int,
    member_user_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_TEAM_MANAGE)
    org_id = auth.require_organization_id()
    SalesCollaborationService(db).remove_member(
        organization_id=org_id,
        user_id=_uid(auth),
        team_id=team_id,
        member_user_id=member_user_id,
    )
    db.commit()
    return None


@router.get("/team-dashboard", response_model=TeamDashboardOut)
def team_dashboard(
    team_id: int | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_TEAM_READ)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).team_dashboard(organization_id=org_id, team_id=team_id)


@router.post("/assign", response_model=AssignOut)
def assign(
    body: AssignIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_ASSIGN)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).assign(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    write_audit(db, user_id=_uid(auth), organization_id=org_id, action="sales.assign", module="sales")
    return out


@router.post("/transfer", response_model=TransferOut)
def transfer(
    body: TransferIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_TRANSFER)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).transfer(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    write_audit(db, user_id=_uid(auth), organization_id=org_id, action="sales.transfer", module="sales")
    return out


@router.get("/comments", response_model=list[CommentOut])
def list_comments(
    entity_type: str,
    entity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).list_comments(
        organization_id=org_id, entity_type=entity_type, entity_id=entity_id
    )


@router.post("/comments", response_model=CommentOut, status_code=201)
def create_comment(
    body: CommentCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_COMMENT)
    if "@[" in body.body:
        auth.require(SALES_MENTION)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).create_comment(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    return out


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def update_comment(
    comment_id: int,
    body: CommentUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_COMMENT)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).update_comment(
        organization_id=org_id, user_id=_uid(auth), comment_id=comment_id, data=body
    )
    db.commit()
    return out


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_COMMENT)
    org_id = auth.require_organization_id()
    SalesCollaborationService(db).delete_comment(
        organization_id=org_id, user_id=_uid(auth), comment_id=comment_id
    )
    db.commit()
    return None


@router.get("/mentions/candidates", response_model=list[MentionCandidate])
def mention_candidates(
    q: str = "",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MENTION)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).mention_candidates(organization_id=org_id, q=q)


@router.get("/followers", response_model=list[FollowerOut])
def list_followers(
    entity_type: str,
    entity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).list_followers(
        organization_id=org_id, entity_type=entity_type, entity_id=entity_id
    )


@router.post("/followers", response_model=FollowerOut, status_code=201)
def follow(
    body: FollowIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    uid = _uid(auth)
    if uid is None:
        from fastapi import HTTPException

        raise HTTPException(401, detail={"code": "auth_required", "message": "Auth requise"})
    out = SalesCollaborationService(db).follow(organization_id=org_id, user_id=uid, data=body)
    db.commit()
    return out


@router.delete("/followers", status_code=204)
def unfollow(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    uid = _uid(auth)
    if uid is None:
        from fastapi import HTTPException

        raise HTTPException(401, detail={"code": "auth_required", "message": "Auth requise"})
    SalesCollaborationService(db).unfollow(
        organization_id=org_id, user_id=uid, entity_type=entity_type, entity_id=entity_id
    )
    db.commit()
    return None


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    status: str | None = "pending",
    mine: bool = False,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_REVIEW)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).list_reviews(
        organization_id=org_id,
        user_id=_uid(auth),
        status=status,
        for_reviewer=mine,
    )


@router.post("/reviews", response_model=ReviewOut, status_code=201)
def create_review(
    body: ReviewCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_REVIEW)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).create_review(
        organization_id=org_id, user_id=_uid(auth), data=body
    )
    db.commit()
    write_audit(db, user_id=_uid(auth), organization_id=org_id, action="sales.review.requested", module="sales")
    return out


@router.post("/reviews/{review_id}/decide", response_model=ReviewOut)
def decide_review(
    review_id: int,
    body: ReviewDecide,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_REVIEW)
    org_id = auth.require_organization_id()
    out = SalesCollaborationService(db).decide_review(
        organization_id=org_id, user_id=_uid(auth), review_id=review_id, data=body
    )
    db.commit()
    write_audit(db, user_id=_uid(auth), organization_id=org_id, action=f"sales.review.{body.decision}", module="sales")
    return out


@router.get("/views")
def collab_views(
    view: str = Query("mine"),
    resource: str = Query("opportunities"),
    team_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return SalesCollaborationService(db).collab_view(
        organization_id=org_id,
        user_id=_uid(auth),
        view=view,
        resource=resource,
        team_id=team_id,
        page=page,
        page_size=page_size,
    )
