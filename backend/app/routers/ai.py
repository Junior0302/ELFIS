from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import bootstrap_ai_tasks
from app.ai.ai_exceptions import AINotFoundError
from app.ai.ai_schemas import DocumentAnalyzeRequest
from app.ai.document_analysis_service import DocumentAnalysisService
from app.ai_assistant.decision_engine import DecisionEngine
from app.ai_assistant.feedback import record_feedback
from app.ai_assistant.memory import ConversationMemory
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    stream: bool = False


class FeedbackIn(BaseModel):
    message_id: str = Field(min_length=8, max_length=64)
    kind: str = Field(pattern="^(useful|useless|incorrect)$")
    comment: str = Field(default="", max_length=2000)


def _require_ai_permission(auth: AuthContext) -> None:
    if auth.user and "ai.analysis" not in auth.permissions and "*" not in auth.permissions:
        raise HTTPException(403, detail="Permission ai.analysis requise")


@router.post("/chat", dependencies=[Depends(require_active_subscription)])
def ai_chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """AI Financial Assistant — Decision Engine (jamais de dialogue direct moteurs ↔ LLM)."""
    _require_ai_permission(auth)
    org_id = auth.require_organization_id()
    user_id = auth.user.id if auth.user else None
    engine = DecisionEngine(db)

    if payload.stream:
        def event_stream():
            for chunk in engine.stream_chat(
                organization_id=org_id, user_id=user_id, question=payload.question
            ):
                yield f"data: {json.dumps(chunk, default=str, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    result = engine.chat(
        organization_id=org_id,
        user_id=user_id,
        question=payload.question,
    )
    if not result.get("ok"):
        raise HTTPException(400, detail=result.get("error") or "Échec assistant")
    return result


@router.get("/context", dependencies=[Depends(require_active_subscription)])
def ai_context(
    question: str = Query(default="vue d'ensemble", max_length=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _require_ai_permission(auth)
    org_id = auth.require_organization_id()
    context = DecisionEngine(db, use_llm=False).get_context(
        org_id, auth.user.id if auth.user else None, question
    )
    return {"ok": True, "context": context}


@router.get("/tools", dependencies=[Depends(require_active_subscription)])
def ai_tools(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _require_ai_permission(auth)
    org_id = auth.require_organization_id()
    return {"ok": True, "tools": DecisionEngine(db, use_llm=False).list_tools(org_id)}


@router.get("/history", dependencies=[Depends(require_active_subscription)])
def ai_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    org_id = auth.require_organization_id()
    memory = ConversationMemory(db, org_id, auth.user.id)
    return {"ok": True, "items": memory.list_history(limit=limit)}


@router.post("/feedback", dependencies=[Depends(require_active_subscription)])
def ai_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    org_id = auth.require_organization_id()
    try:
        row = record_feedback(
            db,
            organization_id=org_id,
            user_id=auth.user.id,
            message_id=payload.message_id,
            kind=payload.kind,
            comment=payload.comment,
        )
    except LookupError:
        raise HTTPException(404, detail="Message introuvable") from None
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from None
    return {
        "ok": True,
        "feedback": {
            "id": row.id,
            "message_id": row.message_id,
            "kind": row.kind,
            "comment": row.comment,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    }


@router.get("/conversations", dependencies=[Depends(require_active_subscription)])
def ai_conversations(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Historique legacy (AIConversation) — conservé pour compatibilité Copilote."""
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    if not auth.organization_id:
        raise HTTPException(400, detail="Organisation non sélectionnée")
    from app.services.finance_agent import list_conversations

    return {"conversations": list_conversations(db, auth.organization_id)}


@router.get("/suggestions")
def ai_suggestions(auth: AuthContext = Depends(get_auth_context)):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    return {
        "agent": "AI Financial Assistant",
        "suggestions": [
            "Que peux-tu faire ?",
            "Quel est l'état de ma trésorerie ?",
            "Résume ma santé financière",
            "Quels clients sont en retard ?",
            "Où en est ma TVA estimée ?",
            "Quelles sont mes principales dépenses ?",
            "Y a-t-il des documents à traiter ?",
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
