from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import bootstrap_ai_tasks
from app.ai.ai_exceptions import AINotFoundError
from app.ai.ai_schemas import DocumentAnalyzeRequest
from app.ai.document_analysis_service import DocumentAnalysisService
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.services.finance_agent import answer_finance_question, list_conversations

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@router.post("/chat", dependencies=[Depends(require_active_subscription)])
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


@router.get("/conversations", dependencies=[Depends(require_active_subscription)])
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
def ai_suggestions(auth: AuthContext = Depends(get_auth_context)):
    """Liste statique — auth requise, abonnement non bloquant."""
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
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


@router.post(
    "/documents/{vault_document_id}/analyze",
    status_code=202,
    dependencies=[Depends(require_active_subscription)],
)
def analyze_vault_document(
    vault_document_id: str,
    payload: DocumentAnalyzeRequest | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Démarre une analyse IA (classification → extraction → quality). 202 Accepted."""
    bootstrap_ai_tasks()
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    body = payload or DocumentAnalyzeRequest()
    try:
        result = DocumentAnalysisService(db).start_analysis(
            organization_id=org_id,
            user_id=auth.user.id,
            vault_document_id=vault_document_id,
            extracted_text=body.extracted_text,
            filename=body.filename,
        )
    except AINotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    return result.model_dump()


@router.get(
    "/documents/{vault_document_id}/analysis",
    dependencies=[Depends(require_active_subscription)],
)
def get_vault_document_analysis(
    vault_document_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    bootstrap_ai_tasks()
    org_id = auth.require_organization_id()
    try:
        view = DocumentAnalysisService(db).get_analysis_for_document(
            organization_id=org_id,
            vault_document_id=vault_document_id,
        )
    except AINotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    return view.model_dump()
