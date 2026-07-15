from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.pipeline import get_or_create_settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.schemas import CompanySettingsIn, CompanySettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=CompanySettingsOut)
def get_settings(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("settings.manage")
    return get_or_create_settings(db, auth.organization_id or 0)


@router.put("", response_model=CompanySettingsOut)
def update_settings(
    payload: CompanySettingsIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("settings.manage")
    row = get_or_create_settings(db, auth.organization_id or 0)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row