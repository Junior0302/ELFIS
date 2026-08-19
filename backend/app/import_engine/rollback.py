"""Rollback Service — annulation des objets créés / liaisons."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.import_engine.enums import ImportArtifactAction, RollbackReason
from app.import_engine.exceptions import ImportRollbackError
from app.import_engine.models import ElfisImportArtifact, ElfisImportRun
from app.models import BankAccount, BankTransaction, Invoice
from app.models_saas import Contact


class RollbackService:
    def __init__(self, db: Session):
        self._db = db

    def rollback_run(
        self,
        run: ElfisImportRun,
        *,
        reason: str = RollbackReason.MANUAL.value,
        actor_user_id: int | None = None,
    ) -> ElfisImportRun:
        artifacts = (
            self._db.query(ElfisImportArtifact)
            .filter(ElfisImportArtifact.import_run_id == run.id)
            .filter(ElfisImportArtifact.rolled_back.is_(False))
            .order_by(ElfisImportArtifact.created_at.desc())
            .all()
        )
        errors: list[str] = []
        for art in artifacts:
            try:
                self._rollback_artifact(art)
                art.rolled_back = True
                art.rolled_back_at = datetime.utcnow()
                self._db.add(art)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{art.entity_kind}:{art.entity_id}:{exc}")

        if errors:
            raise ImportRollbackError(
                "Rollback incomplet: " + "; ".join(errors[:5])
            )

        from app.import_engine.idempotency import deactivate_fingerprint_for_run

        deactivate_fingerprint_for_run(self._db, import_run_id=run.id)
        run.rollback_reason = reason
        run.rolled_back_at = datetime.utcnow()
        self._db.add(run)
        self._db.flush()
        return run

    def _rollback_artifact(self, art: ElfisImportArtifact) -> None:
        kind = art.entity_kind
        eid = art.entity_id
        action = art.action

        if action == ImportArtifactAction.CREATED.value:
            if kind in {
                "invoice",
                "quote",
                "credit_note",
                "receipt",
                "contract",
                "generic",
                "bank_statement",
            }:
                row = self._db.query(Invoice).filter(Invoice.id == int(eid)).first()
                if row and row.organization_id == art.organization_id:
                    self._db.delete(row)
            elif kind == "contact":
                row = self._db.query(Contact).filter(Contact.id == int(eid)).first()
                if row and row.organization_id == art.organization_id:
                    # ne pas supprimer un contact aussi lié ailleurs
                    snap = art.snapshot_json or {}
                    if snap.get("created_by_import"):
                        self._db.delete(row)
            elif kind == "bank_account":
                row = (
                    self._db.query(BankAccount)
                    .filter(BankAccount.id == int(eid))
                    .first()
                )
                if row and row.organization_id == art.organization_id:
                    self._db.delete(row)
            elif kind == "bank_transaction":
                row = (
                    self._db.query(BankTransaction)
                    .filter(BankTransaction.id == int(eid))
                    .first()
                )
                if row:
                    self._db.delete(row)
            # accounting_entry est embarqué dans Invoice — rien à faire
            return

        if action == ImportArtifactAction.LINKED.value and kind == "contact":
            inv_id = (art.snapshot_json or {}).get("invoice_id")
            role = (art.snapshot_json or {}).get("role")
            if inv_id:
                inv = self._db.query(Invoice).filter(Invoice.id == int(inv_id)).first()
                if inv and inv.organization_id == art.organization_id:
                    if role == "supplier":
                        inv.supplier_contact_id = None
                    elif role == "customer":
                        inv.customer_contact_id = None
                    self._db.add(inv)
