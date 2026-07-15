from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.modules.registry import get_module, get_modules
from app.services.banking import (
    bank_overview,
    cashflow_forecast,
    connect_bank,
    import_bank_csv,
    sync_bank,
)

router = APIRouter(prefix="/modules", tags=["modules"])


class BankTxOut(BaseModel):
    id: int
    booked_at: str
    label: str
    amount: float
    category: str
    is_duplicate: bool
    is_anomaly: bool
    anomaly_reason: str | None
    reconciled: bool
    matched_invoice_id: int | None
    confidence: float

    model_config = {"from_attributes": True}


class BankAccountOut(BaseModel):
    id: int
    label: str
    bank_name: str
    iban: str
    currency: str
    balance: float
    connected: bool
    last_sync_at: datetime | None

    model_config = {"from_attributes": True}


class BankConnectIn(BaseModel):
    bank_name: str = Field(min_length=2, max_length=120)
    label: str = "Compte courant"
    iban: str = ""
    balance: float = 0.0


@router.get("")
def list_modules():
    return {
        "product": "ComptaPilot IA",
        "vision": "Copilote financier intelligent du dirigeant — ELFIS Core / KATUKU GROUP",
        "modules": get_modules(),
    }


@router.get("/banque/overview")
def banque_overview(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.read")
    data = bank_overview(db, auth.organization_id)
    account = data["account"]
    return {
        "module": get_module("banque"),
        "account": BankAccountOut.model_validate(account) if account else None,
        "stats": {
            "count": data["count"],
            "credits": data["credits"],
            "debits": data["debits"],
            "to_reconcile": data["to_reconcile"],
            "duplicates": data["duplicates"],
            "anomalies": data["anomalies"],
        },
        "transactions": [BankTxOut.model_validate(t) for t in data["transactions"]],
    }


@router.post("/banque/connect")
def banque_connect(
    payload: BankConnectIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.connect")
    account = connect_bank(
        db,
        bank_name=payload.bank_name,
        label=payload.label,
        iban=payload.iban,
        balance=payload.balance,
        organization_id=auth.organization_id or 0,
    )
    data = bank_overview(db, auth.organization_id)
    return {
        "ok": True,
        "account": BankAccountOut.model_validate(account),
        "stats": {
            "count": data["count"],
            "credits": data["credits"],
            "debits": data["debits"],
            "to_reconcile": data["to_reconcile"],
            "duplicates": data["duplicates"],
            "anomalies": data["anomalies"],
        },
        "message": "Compte enregistré. Importez maintenant le CSV de vos opérations bancaires.",
    }


@router.post("/banque/sync")
def banque_sync(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.connect")
    try:
        result = sync_bank(db, auth.organization_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    data = bank_overview(db, auth.organization_id)
    imported = int(result["imported"])
    analyzed = int(result["analyzed"])
    return {
        "ok": True,
        "account": BankAccountOut.model_validate(result["account"]),
        "imported": imported,
        "analyzed": analyzed,
        "message": (
            f"{imported} nouvelle(s) opération(s) importée(s), {analyzed} analysée(s)."
            if imported
            else (
                "Aucune opération à analyser. Importez d’abord un export CSV de votre banque."
                if analyzed == 0
                else f"{analyzed} opération(s) réanalysée(s)."
            )
        ),
        "stats": {
            "count": data["count"],
            "credits": data["credits"],
            "debits": data["debits"],
            "to_reconcile": data["to_reconcile"],
            "duplicates": data["duplicates"],
            "anomalies": data["anomalies"],
        },
    }


@router.post("/banque/import-csv")
async def banque_import_csv(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("bank.connect")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, detail="Sélectionnez un fichier CSV.")
    content = await file.read()
    if not content:
        raise HTTPException(400, detail="Le fichier CSV est vide.")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, detail="Le fichier CSV dépasse 5 Mo.")
    try:
        result = import_bank_csv(
            db,
            content=content,
            organization_id=auth.organization_id or 0,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {
        "ok": True,
        **result,
        "message": (
            f"{result['imported']} opération(s) réelle(s) importée(s) et analysée(s)."
            if result["imported"]
            else "Aucune nouvelle opération. Les lignes déjà présentes ont été ignorées."
        ),
    }


@router.get("/tresorerie/overview")
def tresorerie_overview(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("finance.read")
    forecast = cashflow_forecast(db, auth.organization_id)
    return {
        "module": get_module("tresorerie"),
        **forecast,
    }


@router.get("/{slug}")
def module_detail(slug: str):
    mod = get_module(slug)
    if not mod:
        raise HTTPException(404, detail="Module introuvable")
    return mod
