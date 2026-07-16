from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.services.finance_agent import answer_finance_question, list_conversations

router = APIRouter(
    prefix="/ai", tags=["ai"], dependencies=[Depends(require_active_subscription)]
)


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@router.post("/chat")
def ai_chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    if auth.user and "ai.analysis" not in auth.permissions and "*" not in auth.permissions:
        raise HTTPException(403, detail="Permission ai.analysis requise")

    org_id = auth.require_organization_id()

    result = answer_finance_question(
        db,
        question=payload.question,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
    )
    return {"ok": True, **result}


@router.get("/conversations")
def ai_conversations(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    if not auth.organization_id:
        raise HTTPException(400, detail="Organisation non sélectionnée")
    return {"conversations": list_conversations(db, auth.organization_id)}


@router.get("/suggestions")
def ai_suggestions():
    return {
        "agent": "Finance Agent",
        "suggestions": [
            "Que peux-tu faire ?",
            "Quel est l'état de ma trésorerie ?",
            "Pourquoi ma marge baisse-t-elle ?",
            "Quels clients sont en retard ?",
            "Puis-je acheter un véhicule à 40 000 € ?",
            "Où en est ma TVA récupérable ?",
        ],
    }
