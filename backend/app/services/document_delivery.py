"""Orchestration envoi facture/devis/avoir : PDF → Vault → e-mail avec PJ."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.events import EventNames, bootstrap_handlers, safe_publish
from app.events.event_context import new_correlation_id
from app.events.event_schemas import DomainEvent
from app.models_saas import DocumentEmailLog, Organization, SalesDocument
from app.repositories.vault_repository import VaultRepository
from app.schemas_vault import VaultActivityAction, VaultDocumentType, VaultEmailStatus
from app.services.org_email_settings import is_valid_email
from app.services.sales_email import send_sales_document_email
from app.services.sales_pdf import sales_document_to_pdf
from app.services.vault.exceptions import (
    VaultAccessDeniedError,
    VaultStorageError,
)
from app.services.vault.vault_access_service import assert_can_deliver
from app.services.vault.vault_service import archive_or_reuse_pdf

logger = logging.getLogger(__name__)


def _parse_doc_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None

DOC_TYPE_TO_VAULT: dict[str, VaultDocumentType] = {
    "facture": VaultDocumentType.customer_invoice,
    "devis": VaultDocumentType.quote,
    "avoir": VaultDocumentType.credit_note,
}

BUSINESS_TYPE_LABEL: dict[str, str] = {
    "facture": "invoice",
    "devis": "quote",
    "avoir": "credit_note",
}


class DocumentDeliveryError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class DocumentDeliveryResult:
    status: str
    business_document_id: int
    business_document_type: str
    vault_document_id: str | None
    vault_archive_status: str | None
    email_status: str
    recipient: str
    sent_at: datetime | None
    reused_existing_archive: bool
    email_log: DocumentEmailLog | None
    already_processed: bool = False
    message: str = ""


def delivery_attachment_filename(doc: SalesDocument) -> str:
    prefix = {"facture": "facture", "devis": "devis", "avoir": "avoir"}.get(
        doc.doc_type, "document"
    )
    safe_num = re.sub(r"[^\w.-]+", "-", (doc.number or "sans-numero")).strip("-") or "sans-numero"
    return f"{prefix}-{safe_num}.pdf"


def _recipient_domain(email: str) -> str:
    parts = (email or "").strip().split("@", 1)
    return parts[1].lower() if len(parts) == 2 else ""


def _build_idempotency_key(
    *,
    organization_id: int,
    doc_type: str,
    doc_id: int,
    recipient: str,
    version: int,
    explicit: str | None,
) -> str:
    if explicit and explicit.strip():
        return explicit.strip()[:128]
    raw = f"{organization_id}:{doc_type}:{doc_id}:{recipient.strip().lower()}:{version}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def _safe_log(
    repo: VaultRepository,
    *,
    organization_id: int,
    document_id: str,
    user_id: int | None,
    action: VaultActivityAction,
    metadata: dict,
) -> None:
    try:
        repo.create_activity_log(
            organization_id=organization_id,
            document_id=document_id,
            user_id=user_id,
            action=action,
            metadata=metadata,
        )
    except Exception:
        logger.exception("document_delivery_activity_log_failed", extra={"action": action.value})


class DocumentDeliveryService:
    """Envoie un document de vente avec archivage Vault automatique."""

    def __init__(self, db: Session):
        self._db = db
        bootstrap_handlers()

    def _publish(
        self,
        *,
        event_name: str,
        organization_id: int,
        payload: dict,
        metadata: dict,
        idempotency_key: str | None,
        correlation_id: str,
        causation_id: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
    ) -> None:
        """
        Publication complémentaire (non bloquante).

        Limite transactionnelle : VaultRepository et sales_email commitent déjà
        leurs propres transactions ; l'événement n'est pas dans la même TX métier.
        """
        safe_publish(
            self._db,
            DomainEvent(
                event_name=event_name,
                organization_id=organization_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                metadata=metadata,
                idempotency_key=idempotency_key,
                correlation_id=uuid.UUID(correlation_id),
                causation_id=uuid.UUID(causation_id) if causation_id else None,
            ),
        )

    def send_document(
        self,
        *,
        document_type: str,
        document_id: int,
        organization_id: int,
        authenticated_user_id: int,
        recipient_email: str,
        cc: str | None = None,
        bcc: str | None = None,
        subject: str | None = None,
        body: str = "",
        idempotency_key: str | None = None,
        connection_id: int | None = None,
        preferred_from_email: str | None = None,
        preferred_from_label: str | None = None,
        is_test: bool = False,
    ) -> DocumentDeliveryResult:
        doc_type = (document_type or "").strip().lower()
        if doc_type not in DOC_TYPE_TO_VAULT:
            raise DocumentDeliveryError("invalid_type", "Type de document non supporté")

        try:
            assert_can_deliver(
                self._db, user_id=authenticated_user_id, organization_id=organization_id
            )
        except VaultAccessDeniedError as exc:
            raise DocumentDeliveryError("forbidden", str(exc)) from exc

        doc = (
            self._db.query(SalesDocument)
            .filter(
                SalesDocument.id == document_id,
                SalesDocument.organization_id == organization_id,
                SalesDocument.doc_type == doc_type,
            )
            .first()
        )
        if not doc:
            raise DocumentDeliveryError("not_found", "Document introuvable")

        to_email = (recipient_email or doc.customer_email or "").strip()
        if not to_email or not is_valid_email(to_email):
            raise DocumentDeliveryError(
                "missing_recipient",
                "Ajoutez une adresse e-mail au client avant l’envoi.",
            )
        if subject and len(subject) > 200:
            raise DocumentDeliveryError("invalid_subject", "Sujet trop long (max 200 caractères)")
        if body and len(body) > 20_000:
            raise DocumentDeliveryError("invalid_body", "Corps du message trop long")
        for label, value in (("cc", cc), ("bcc", bcc)):
            if value and len([p for p in value.split(",") if p.strip()]) > 5:
                raise DocumentDeliveryError(
                    "too_many_recipients",
                    f"Trop de destinataires {label.upper()} (max 5).",
                )

        key = _build_idempotency_key(
            organization_id=organization_id,
            doc_type=doc_type,
            doc_id=doc.id,
            recipient=to_email,
            version=1,
            explicit=idempotency_key,
        )

        recent = (
            self._db.query(DocumentEmailLog)
            .filter(
                DocumentEmailLog.organization_id == organization_id,
                DocumentEmailLog.idempotency_key == key,
                DocumentEmailLog.status.in_(("preparing", "queued", "sent", "delivered", "opened")),
            )
            .order_by(DocumentEmailLog.id.desc())
            .first()
        )
        if recent and recent.status in ("sent", "delivered", "opened"):
            return DocumentDeliveryResult(
                status="already_sent",
                business_document_id=doc.id,
                business_document_type=BUSINESS_TYPE_LABEL[doc_type],
                vault_document_id=None,
                vault_archive_status=None,
                email_status="sent",
                recipient=to_email,
                sent_at=recent.sent_at,
                reused_existing_archive=False,
                email_log=recent,
                already_processed=True,
                message="Cet envoi a déjà été traité.",
            )
        if recent and recent.status in ("preparing", "queued"):
            raise DocumentDeliveryError(
                "in_progress",
                "Un envoi est déjà en cours pour ce document. Réessayez dans un instant.",
            )

        organization = self._db.get(Organization, organization_id)
        if not organization:
            raise DocumentDeliveryError("org_not_found", "Organisation introuvable")

        try:
            pdf_bytes = sales_document_to_pdf(doc, organization)
            if not pdf_bytes or len(pdf_bytes) < 20:
                raise RuntimeError("PDF indisponible")
            if len(pdf_bytes) > 14 * 1024 * 1024:
                raise RuntimeError("PDF trop volumineux")
        except Exception as exc:
            logger.exception("document_delivery_pdf_failed")
            raise DocumentDeliveryError(
                "pdf_error",
                "Le document PDF n’a pas pu être généré. Veuillez réessayer.",
            ) from exc

        attachment_name = delivery_attachment_filename(doc)
        vault_type = DOC_TYPE_TO_VAULT[doc_type]
        repo = VaultRepository(self._db)
        correlation_id = new_correlation_id()
        actor_meta = {
            "source": "document_delivery",
            "actor_user_id": str(authenticated_user_id),
            "request_id": None,
        }

        try:
            vault_doc, reused = archive_or_reuse_pdf(
                self._db,
                user_id=authenticated_user_id,
                organization_id=organization_id,
                document_type=vault_type,
                document_number=doc.number,
                filename=attachment_name,
                content=pdf_bytes,
                invoice_date=_parse_doc_date(doc.issue_date),
                due_date=_parse_doc_date(doc.due_date),
                amount_ht=Decimal(str(doc.amount_ht)) if doc.amount_ht is not None else None,
                amount_vat=Decimal(str(doc.amount_tva)) if doc.amount_tva is not None else None,
                amount_ttc=Decimal(str(doc.amount_ttc)) if doc.amount_ttc is not None else None,
                currency=(organization.currency or "EUR")[:3],
                customer_id=doc.customer_id,
                email_status=VaultEmailStatus.pending.value,
                skip_access_check=True,
            )
        except VaultStorageError as exc:
            raise DocumentDeliveryError(
                "archive_failed",
                "Le document n’a pas pu être archivé. L’e-mail n’a pas été envoyé.",
            ) from exc
        except VaultAccessDeniedError as exc:
            raise DocumentDeliveryError("forbidden", str(exc)) from exc
        except Exception as exc:
            logger.exception("document_delivery_archive_failed")
            raise DocumentDeliveryError(
                "archive_failed",
                "Le document n’a pas pu être archivé. L’e-mail n’a pas été envoyé.",
            ) from exc

        archive_payload = {
            "vault_document_id": vault_doc.id,
            "business_document_id": str(doc.id),
            "business_document_type": BUSINESS_TYPE_LABEL[doc_type],
            "document_type": vault_type.value,
            "archive_status": vault_doc.archive_status,
            "reused_existing_archive": reused,
        }
        if reused:
            self._publish(
                event_name=EventNames.VAULT_DOCUMENT_REUSED,
                organization_id=organization_id,
                payload=archive_payload,
                metadata=actor_meta,
                idempotency_key=f"vault:reused:{organization_id}:{vault_doc.id}:{key}",
                correlation_id=correlation_id,
                aggregate_type="vault_document",
                aggregate_id=vault_doc.id,
            )
        else:
            self._publish(
                event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
                organization_id=organization_id,
                payload=archive_payload,
                metadata=actor_meta,
                idempotency_key=f"vault:archived:{organization_id}:{vault_doc.id}:{key}",
                correlation_id=correlation_id,
                aggregate_type="vault_document",
                aggregate_id=vault_doc.id,
            )

        meta_base = {
            "business_document_id": str(doc.id),
            "business_document_type": BUSINESS_TYPE_LABEL[doc_type],
            "recipient_domain": _recipient_domain(to_email),
            "vault_document_id": vault_doc.id,
            "source": "document_delivery",
        }
        _safe_log(
            repo,
            organization_id=organization_id,
            document_id=vault_doc.id,
            user_id=authenticated_user_id,
            action=VaultActivityAction.email_send_started,
            metadata=meta_base,
        )

        email_payload = {
            "vault_document_id": vault_doc.id,
            "business_document_id": str(doc.id),
            "business_document_type": BUSINESS_TYPE_LABEL[doc_type],
            "document_type": vault_type.value,
            "recipient_domain": _recipient_domain(to_email),
        }
        self._publish(
            event_name=EventNames.DELIVERY_EMAIL_STARTED,
            organization_id=organization_id,
            payload=email_payload,
            metadata=actor_meta,
            idempotency_key=f"delivery:email_started:{organization_id}:{doc.id}:{key}",
            correlation_id=correlation_id,
            aggregate_type="sales_document",
            aggregate_id=str(doc.id),
        )

        email_log = send_sales_document_email(
            self._db,
            doc,
            recipient=to_email,
            message=body or "",
            subject=subject,
            cc=cc,
            bcc=bcc,
            sent_by_user_id=authenticated_user_id,
            is_test=is_test,
            idempotency_key=key,
            connection_id=connection_id,
            preferred_from_email=preferred_from_email,
            preferred_from_label=preferred_from_label,
            pdf_bytes=pdf_bytes,
            attachment_filename=attachment_name,
        )

        if email_log.status in ("sent", "delivered", "opened", "queued"):
            updated = repo.update_email_status(
                document_id=vault_doc.id,
                organization_id=organization_id,
                email_status=VaultEmailStatus.sent.value,
            )
            if updated:
                vault_doc = updated
            else:
                vault_doc.email_status = VaultEmailStatus.sent.value
            _safe_log(
                repo,
                organization_id=organization_id,
                document_id=vault_doc.id,
                user_id=authenticated_user_id,
                action=VaultActivityAction.email_sent,
                metadata=meta_base,
            )
            self._publish(
                event_name=EventNames.DELIVERY_EMAIL_SENT,
                organization_id=organization_id,
                payload={
                    **email_payload,
                    "email_log_id": str(email_log.id) if email_log.id else None,
                    "email_status": "sent",
                },
                metadata=actor_meta,
                idempotency_key=f"delivery:email_sent:{organization_id}:{doc.id}:{email_log.id or key}",
                correlation_id=correlation_id,
                aggregate_type="sales_document",
                aggregate_id=str(doc.id),
            )
            return DocumentDeliveryResult(
                status="sent",
                business_document_id=doc.id,
                business_document_type=BUSINESS_TYPE_LABEL[doc_type],
                vault_document_id=vault_doc.id,
                vault_archive_status=vault_doc.archive_status,
                email_status=vault_doc.email_status,
                recipient=to_email,
                sent_at=email_log.sent_at,
                reused_existing_archive=reused,
                email_log=email_log,
                message="",
            )

        updated = repo.update_email_status(
            document_id=vault_doc.id,
            organization_id=organization_id,
            email_status=VaultEmailStatus.failed.value,
        )
        if updated:
            vault_doc = updated
        else:
            vault_doc.email_status = VaultEmailStatus.failed.value
        _safe_log(
            repo,
            organization_id=organization_id,
            document_id=vault_doc.id,
            user_id=authenticated_user_id,
            action=VaultActivityAction.email_failed,
            metadata={**meta_base, "error_code": email_log.error_code or "provider_error"},
        )
        self._publish(
            event_name=EventNames.DELIVERY_EMAIL_FAILED,
            organization_id=organization_id,
            payload={
                **email_payload,
                "email_log_id": str(email_log.id) if email_log.id else None,
                "email_status": "failed",
                "error_code": email_log.error_code or "provider_error",
            },
            metadata=actor_meta,
            idempotency_key=f"delivery:email_failed:{organization_id}:{doc.id}:{email_log.id or key}",
            correlation_id=correlation_id,
            aggregate_type="sales_document",
            aggregate_id=str(doc.id),
        )
        return DocumentDeliveryResult(
            status="email_failed",
            business_document_id=doc.id,
            business_document_type=BUSINESS_TYPE_LABEL[doc_type],
            vault_document_id=vault_doc.id,
            vault_archive_status=vault_doc.archive_status,
            email_status=vault_doc.email_status,
            recipient=to_email,
            sent_at=email_log.sent_at,
            reused_existing_archive=reused,
            email_log=email_log,
            message=(
                "Le document a été archivé, mais l’e-mail n’a pas pu être envoyé. "
                "Vous pourrez réessayer sans recréer la facture."
            ),
        )
