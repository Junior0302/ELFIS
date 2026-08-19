"""Pipeline d'import atomique."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.document_extraction.models import ElfisDocumentExtraction
from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.import_engine.audit import write_import_audit
from app.import_engine.enums import (
    ImportArtifactAction,
    ImportRunStatus,
    RollbackReason,
)
from app.import_engine.events import publish_import_event
from app.import_engine.exceptions import ImportEngineError, ImportStateError
from app.import_engine.idempotency import (
    assert_not_already_imported,
    register_fingerprint,
)
from app.import_engine.mapping import MappingEngine
from app.import_engine.models import (
    ElfisImportArtifact,
    ElfisImportReport,
    ElfisImportRun,
)
from app.import_engine.rollback import RollbackService
from app.models import BankAccount, BankTransaction, Invoice
from app.models_saas import Contact
from app.services.contacts.validators import (
    require_minimal_identity,
    validate_optional_identifiers,
)
from app.validation_mapping.enums import MatchResolution
from app.validation_mapping.models import ElfisValidationMatch, ElfisValidationSession


class ImportPipeline:
    def __init__(self, db: Session):
        self._db = db
        self._mapper = MappingEngine()
        self._lifecycle = DocumentLifecycleService(db)

    def execute(
        self,
        run: ElfisImportRun,
        *,
        item: Any,
        session: ElfisValidationSession,
        actor_user_id: int | None,
    ) -> ElfisImportRun:
        t0 = time.perf_counter()
        org_id = int(run.organization_id)
        actor_kw = {
            "organization_id": org_id,
            "actor_user_id": actor_user_id,
            "commit": False,
        }
        try:
            assert_not_already_imported(
                self._db, organization_id=org_id, fingerprint=run.fingerprint
            )

            self._set_status(run, ImportRunStatus.MAPPING.value, progress=10)
            publish_import_event(
                self._db,
                event_type="import.started",
                run=run,
                actor_user_id=actor_user_id,
            )

            if item.lifecycle_status in {
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
                DocumentLifecycleStatus.IMPORT_FAILED.value,
                DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
            }:
                self._lifecycle.mark_import_pending(
                    item, reason_code="import_pipeline", **actor_kw
                )

            extr = (
                self._db.query(ElfisDocumentExtraction)
                .filter(ElfisDocumentExtraction.id == session.extraction_id)
                .first()
            )
            schema_name = (extr.schema_name if extr else None) or "generic_document.v1"
            run.schema_name = schema_name
            run.extraction_id = session.extraction_id

            mapped = self._mapper.map(
                schema_name=schema_name,
                validated_data=dict(session.validated_data or {}),
                filename=item.original_filename,
                stored_path=item.storage_key or item.storage_location or "",
                mime_type=item.mime or "application/octet-stream",
            )
            run.warnings_json = list(mapped.warnings)
            self._set_status(run, ImportRunStatus.MAPPING.value, progress=25)
            publish_import_event(
                self._db,
                event_type="import.mapping.completed",
                run=run,
                actor_user_id=actor_user_id,
                metadata={"schema_name": schema_name},
            )

            self._lifecycle.mark_importing(
                item, reason_code="import_transaction", **actor_kw
            )
            self._set_status(
                run, ImportRunStatus.TRANSACTION_STARTED.value, progress=35
            )
            publish_import_event(
                self._db,
                event_type="import.transaction.started",
                run=run,
                actor_user_id=actor_user_id,
            )

            created: list[dict[str, Any]] = []
            linked: list[dict[str, Any]] = []

            invoice = Invoice(
                organization_id=org_id,
                **mapped.invoice_fields,
            )
            self._db.add(invoice)
            self._db.flush()
            self._add_artifact(
                run,
                entity_kind=mapped.kind,
                entity_id=str(invoice.id),
                action=ImportArtifactAction.CREATED.value,
                label=invoice.invoice_number or invoice.filename,
                snapshot={"created_by_import": True, "kind": mapped.kind},
            )
            created.append(
                {
                    "kind": mapped.kind,
                    "id": invoice.id,
                    "label": invoice.invoice_number or invoice.filename,
                }
            )
            write_import_audit(
                self._db,
                organization_id=org_id,
                action="entity_created",
                import_run_id=run.id,
                entity_kind=mapped.kind,
                entity_id=str(invoice.id),
                actor_user_id=actor_user_id,
            )

            if mapped.accounting_entry:
                self._add_artifact(
                    run,
                    entity_kind="accounting_entry",
                    entity_id=str(invoice.id),
                    action=ImportArtifactAction.CREATED.value,
                    label="accounting_entry",
                    snapshot=mapped.accounting_entry,
                )
                created.append(
                    {"kind": "accounting_entry", "id": invoice.id, "label": "entry"}
                )

            matches = (
                self._db.query(ElfisValidationMatch)
                .filter(ElfisValidationMatch.validation_session_id == session.id)
                .all()
            )
            for match in matches:
                if match.resolution == MatchResolution.IGNORE.value:
                    continue
                if match.resolution == MatchResolution.USE_EXISTING.value:
                    contact = (
                        self._db.query(Contact)
                        .filter(Contact.id == match.contact_id)
                        .filter(Contact.organization_id == org_id)
                        .first()
                    )
                    if not contact:
                        raise ImportStateError(
                            f"Contact {match.contact_id} introuvable"
                        )
                    self._link_invoice_contact(invoice, contact, match.party_role)
                    self._add_artifact(
                        run,
                        entity_kind="contact",
                        entity_id=str(contact.id),
                        action=ImportArtifactAction.LINKED.value,
                        label=contact.company_name or str(contact.id),
                        snapshot={
                            "invoice_id": invoice.id,
                            "role": match.party_role,
                            "resolution": "use_existing",
                        },
                    )
                    linked.append(
                        {
                            "kind": "contact",
                            "id": contact.id,
                            "role": match.party_role,
                            "resolution": "use_existing",
                        }
                    )
                    write_import_audit(
                        self._db,
                        organization_id=org_id,
                        action="entity_linked",
                        import_run_id=run.id,
                        entity_kind="contact",
                        entity_id=str(contact.id),
                        actor_user_id=actor_user_id,
                        detail={"role": match.party_role},
                    )
                elif match.resolution == MatchResolution.CREATE_LATER.value:
                    candidate = mapped.contact_candidates.get(
                        match.party_role
                    ) or mapped.contact_candidates.get("supplier")
                    if not candidate:
                        raise ImportStateError(
                            f"Données contact manquantes pour créer {match.party_role}"
                        )
                    contact = self._create_contact(
                        organization_id=org_id,
                        user_id=actor_user_id,
                        role=match.party_role,
                        data=candidate,
                        source_document_id=invoice.id,
                    )
                    self._link_invoice_contact(invoice, contact, match.party_role)
                    self._add_artifact(
                        run,
                        entity_kind="contact",
                        entity_id=str(contact.id),
                        action=ImportArtifactAction.CREATED.value,
                        label=contact.company_name or str(contact.id),
                        snapshot={
                            "created_by_import": True,
                            "invoice_id": invoice.id,
                            "role": match.party_role,
                        },
                    )
                    created.append(
                        {
                            "kind": "contact",
                            "id": contact.id,
                            "role": match.party_role,
                            "resolution": "create_later",
                        }
                    )
                    write_import_audit(
                        self._db,
                        organization_id=org_id,
                        action="entity_created",
                        import_run_id=run.id,
                        entity_kind="contact",
                        entity_id=str(contact.id),
                        actor_user_id=actor_user_id,
                        detail={"role": match.party_role},
                    )

            if mapped.bank_payload:
                self._import_bank(run, mapped.bank_payload, created, actor_user_id)

            if not invoice.id:
                raise ImportStateError("Invoice non persistée")

            register_fingerprint(
                self._db,
                organization_id=org_id,
                fingerprint=run.fingerprint,
                document_intake_item_id=run.document_intake_item_id,
                validation_session_id=run.validation_session_id,
                validation_version=run.validation_version,
                import_run_id=run.id,
            )

            self._set_status(run, ImportRunStatus.COMMITTING.value, progress=85)

            duration_ms = int((time.perf_counter() - t0) * 1000)
            run.created_objects_json = created
            run.linked_objects_json = linked
            run.duration_ms = duration_ms
            run.completed_at = datetime.utcnow()
            self._set_status(run, ImportRunStatus.COMPLETED.value, progress=100)

            report = ElfisImportReport(
                organization_id=org_id,
                import_run_id=run.id,
                version=1,
                documents_json=[
                    {
                        "document_id": run.document_intake_item_id,
                        "universal_document_id": run.universal_document_id,
                        "schema_name": schema_name,
                    }
                ],
                created_objects_json=created,
                linked_objects_json=linked,
                warnings_json=list(run.warnings_json or []),
                duration_ms=duration_ms,
                actor_user_id=actor_user_id,
                report_json={
                    "status": "completed",
                    "fingerprint": run.fingerprint,
                    "validation_session_id": session.id,
                    "validation_version": session.version,
                },
            )
            self._db.add(report)
            self._db.flush()
            run.report_id = report.id
            self._db.add(run)

            self._lifecycle.mark_import_completed(
                item, reason_code="import_completed", **actor_kw
            )

            publish_import_event(
                self._db,
                event_type="import.transaction.committed",
                run=run,
                actor_user_id=actor_user_id,
            )
            publish_import_event(
                self._db,
                event_type="import.completed",
                run=run,
                actor_user_id=actor_user_id,
                metadata={
                    "created_count": len(created),
                    "linked_count": len(linked),
                    "duration_ms": duration_ms,
                },
            )
            write_import_audit(
                self._db,
                organization_id=org_id,
                action="import_completed",
                import_run_id=run.id,
                actor_user_id=actor_user_id,
            )
            # Commit unique — atomicité totale
            self._db.commit()
            return run

        except Exception as exc:  # noqa: BLE001
            self._db.rollback()
            return self._fail(run, item, exc, actor_user_id, t0)

    def _fail(
        self,
        run: ElfisImportRun,
        item: Any,
        exc: Exception,
        actor_user_id: int | None,
        t0: float,
    ) -> ElfisImportRun:
        run = self._db.query(ElfisImportRun).filter(ElfisImportRun.id == run.id).one()
        code = getattr(exc, "code", None) or type(exc).__name__
        msg = getattr(exc, "message", None) or str(exc)
        run.error_code = str(code)[:64]
        run.error_message = str(msg)[:2000]
        run.duration_ms = int((time.perf_counter() - t0) * 1000)
        run.status = ImportRunStatus.FAILED.value
        run.progress_percent = 100
        run.completed_at = datetime.utcnow()
        self._db.add(run)

        try:
            item = (
                self._db.query(type(item))
                .filter(type(item).id == item.id)
                .first()
            ) or item
            self._db.refresh(item)
            if item.lifecycle_status in {
                DocumentLifecycleStatus.IMPORT_PENDING.value,
                DocumentLifecycleStatus.IMPORTING.value,
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            }:
                self._lifecycle.mark_import_failed(
                    item,
                    organization_id=run.organization_id,
                    actor_user_id=actor_user_id,
                    reason_code="import_failed",
                    commit=False,
                )
        except Exception:  # noqa: BLE001
            pass

        publish_import_event(
            self._db,
            event_type="import.failed",
            run=run,
            actor_user_id=actor_user_id,
            metadata={"error_code": run.error_code},
        )
        write_import_audit(
            self._db,
            organization_id=run.organization_id,
            action="import_failed",
            import_run_id=run.id,
            actor_user_id=actor_user_id,
            reason=run.error_message,
            detail={"error_code": run.error_code},
        )
        self._db.commit()
        if isinstance(exc, ImportEngineError):
            raise exc
        raise ImportStateError(msg) from exc

    def _set_status(
        self, run: ElfisImportRun, status: str, *, progress: int
    ) -> None:
        run.status = status
        run.progress_percent = progress
        run.updated_at = datetime.utcnow()
        self._db.add(run)
        self._db.flush()

    def _add_artifact(
        self,
        run: ElfisImportRun,
        *,
        entity_kind: str,
        entity_id: str,
        action: str,
        label: str | None,
        snapshot: dict[str, Any],
    ) -> ElfisImportArtifact:
        art = ElfisImportArtifact(
            organization_id=run.organization_id,
            import_run_id=run.id,
            entity_kind=entity_kind,
            entity_id=str(entity_id),
            action=action,
            label=label,
            snapshot_json=snapshot,
        )
        self._db.add(art)
        self._db.flush()
        return art

    def _link_invoice_contact(
        self, invoice: Invoice, contact: Contact, role: str
    ) -> None:
        role_clean = (role or "").strip().lower()
        if role_clean in {"supplier", "merchant"}:
            invoice.supplier_contact_id = contact.id
            if not invoice.supplier and contact.company_name:
                invoice.supplier = contact.company_name
        elif role_clean == "customer":
            invoice.customer_contact_id = contact.id
        self._db.add(invoice)
        self._db.flush()

    def _create_contact(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        role: str,
        data: dict[str, Any],
        source_document_id: int,
    ) -> Contact:
        cleaned = validate_optional_identifiers(dict(data))
        require_minimal_identity(cleaned)
        ctype = "supplier" if role in {"supplier", "merchant"} else "customer"
        contact = Contact(
            organization_id=organization_id,
            user_id=user_id,
            contact_type=ctype,
            status="active",
            company_name=cleaned.get("company_name") or "",
            trade_name=cleaned.get("trade_name") or "",
            first_name=cleaned.get("first_name") or "",
            last_name=cleaned.get("last_name") or "",
            siren=cleaned.get("siren") or "",
            siret=cleaned.get("siret") or "",
            vat_number=cleaned.get("vat_number") or "",
            email=cleaned.get("email") or "",
            phone=cleaned.get("phone") or "",
            address_line_1=cleaned.get("address_line_1") or "",
            address_line_2=cleaned.get("address_line_2") or "",
            postal_code=cleaned.get("postal_code") or "",
            city=cleaned.get("city") or "",
            country=cleaned.get("country") or "France",
            iban=cleaned.get("iban") or "",
            bic=cleaned.get("bic") or "",
            source="import_engine",
            source_document_id=source_document_id,
            created_by=user_id,
        )
        self._db.add(contact)
        self._db.flush()
        return contact

    def _import_bank(
        self,
        run: ElfisImportRun,
        payload: dict[str, Any],
        created: list[dict[str, Any]],
        actor_user_id: int | None,
    ) -> None:
        account = BankAccount(
            organization_id=run.organization_id,
            label=str(payload.get("label") or "Compte importé")[:255],
            bank_name=str(payload.get("bank_name") or "")[:255],
            iban=str(payload.get("iban") or "")[:64],
            currency=str(payload.get("currency") or "EUR")[:8],
            balance=0.0,
            connected=False,
        )
        self._db.add(account)
        self._db.flush()
        self._add_artifact(
            run,
            entity_kind="bank_account",
            entity_id=str(account.id),
            action=ImportArtifactAction.CREATED.value,
            label=account.label,
            snapshot={"created_by_import": True},
        )
        created.append(
            {"kind": "bank_account", "id": account.id, "label": account.label}
        )
        for idx, tx in enumerate(payload.get("transactions") or []):
            if not isinstance(tx, dict):
                continue
            amount = float(tx.get("amount") or 0)
            row = BankTransaction(
                account_id=account.id,
                external_id=str(tx.get("external_id") or f"imp-{run.id}-{idx}")[:128],
                booked_at=str(tx.get("booked_at") or tx.get("date") or "")[:32],
                label=str(tx.get("label") or "Transaction importée")[:512],
                amount=amount,
                currency=str(tx.get("currency") or account.currency)[:8],
            )
            self._db.add(row)
            self._db.flush()
            self._add_artifact(
                run,
                entity_kind="bank_transaction",
                entity_id=str(row.id),
                action=ImportArtifactAction.CREATED.value,
                label=row.label,
                snapshot={"created_by_import": True, "account_id": account.id},
            )
            created.append(
                {"kind": "bank_transaction", "id": row.id, "label": row.label}
            )
        write_import_audit(
            self._db,
            organization_id=run.organization_id,
            action="entity_created",
            import_run_id=run.id,
            entity_kind="bank_account",
            entity_id=str(account.id),
            actor_user_id=actor_user_id,
        )
