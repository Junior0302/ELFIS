from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_fiscal import FiscalPeriodRecord
from app.services.auth import write_audit

router = APIRouter(
    prefix="/fiscal",
    tags=["fiscal"],
    dependencies=[Depends(require_active_subscription)],
)

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_KINDS = {"vat_declaration", "period_close"}


class ClosePeriodIn(BaseModel):
    period_key: str
    kind: str = Field(default="period_close")
    notes: str = ""


def _serialize(row: FiscalPeriodRecord) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "period_key": row.period_key,
        "kind": row.kind,
        "status": row.status,
        "notes": row.notes or "",
        "closed_by": row.closed_by,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/periods")
def list_periods(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    org_id = auth.require_organization_id()
    rows = (
        db.query(FiscalPeriodRecord)
        .filter(
            FiscalPeriodRecord.organization_id == org_id,
            FiscalPeriodRecord.status == "closed",
        )
        .order_by(FiscalPeriodRecord.period_key.desc())
        .limit(120)
        .all()
    )
    return {"periods": [_serialize(r) for r in rows]}


@router.post("/periods/close")
def close_period(
    payload: ClosePeriodIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    org_id = auth.require_organization_id()
    period_key = (payload.period_key or "").strip()
    kind = (payload.kind or "period_close").strip()
    if not _PERIOD_RE.match(period_key):
        raise HTTPException(400, detail="period_key invalide (attendu YYYY-MM)")
    if kind not in _KINDS:
        raise HTTPException(400, detail="kind invalide")

    row = (
        db.query(FiscalPeriodRecord)
        .filter(
            FiscalPeriodRecord.organization_id == org_id,
            FiscalPeriodRecord.period_key == period_key,
            FiscalPeriodRecord.kind == kind,
        )
        .first()
    )
    now = datetime.utcnow()
    if row:
        row.status = "closed"
        row.notes = (payload.notes or "").strip()
        row.closed_by = auth.user.id if auth.user else None
        row.closed_at = now
    else:
        row = FiscalPeriodRecord(
            organization_id=org_id,
            period_key=period_key,
            kind=kind,
            status="closed",
            notes=(payload.notes or "").strip(),
            closed_by=auth.user.id if auth.user else None,
            closed_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action=f"fiscal_{kind}_closed:{period_key}",
        module="fiscal",
    )
    return {"period": _serialize(row)}


@router.post("/periods/{period_id}/reopen")
def reopen_period(
    period_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    org_id = auth.require_organization_id()
    row = db.get(FiscalPeriodRecord, period_id)
    if not row or row.organization_id != org_id:
        raise HTTPException(404, detail="Période introuvable")
    row.status = "reopened"
    db.add(row)
    db.commit()
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action=f"fiscal_{row.kind}_reopened:{row.period_key}",
        module="fiscal",
    )
    return {"ok": True}
