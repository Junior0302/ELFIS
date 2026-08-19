"""Indexer clients / fournisseurs (Contact + Customer)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models_saas import Contact, Customer
from app.search.indexers.base import ResourceIndexer
from app.search.search_exceptions import SearchNotFoundError
from app.search.search_schemas import BuiltSearchDocument
from app.search.search_security import (
    assert_action_url,
    content_hash,
    filter_metadata,
    sanitize_indexed_text,
)
from app.search.search_types import SearchCategories, SearchResourceTypes


def _contact_display_name(c: Contact) -> str:
    return (
        c.company_name
        or c.trade_name
        or " ".join(p for p in [c.first_name or "", c.last_name or ""] if p).strip()
        or f"Contact {c.id}"
    )


class CustomerIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.CUSTOMER

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        # Préfixe contact: pour Contact, sinon Customer billing
        if str(resource_id).startswith("contact:"):
            cid = int(str(resource_id).split(":", 1)[1])
            row = db.query(Contact).filter(Contact.id == cid).first()
            if not row or row.organization_id != organization_id:
                raise SearchNotFoundError("Contact introuvable")
            if row.contact_type not in ("customer", "customer_and_supplier", "prospect"):
                raise SearchNotFoundError("Contact non client")
            return ("contact", row)
        cust = db.query(Customer).filter(Customer.id == int(resource_id)).first()
        if not cust or cust.organization_id != organization_id:
            raise SearchNotFoundError("Client introuvable")
        return ("customer", cust)

    def build_search_document(
        self,
        resource: Any,
        *,
        organization_id: int,
        resource_version: int = 1,
    ) -> BuiltSearchDocument:
        kind, obj = resource
        if kind == "contact":
            c: Contact = obj
            title = _contact_display_name(c)
            search_text = sanitize_indexed_text(
                "\n".join(
                    [
                        title,
                        c.email or "",
                        c.phone or "",
                        c.siret or "",
                        c.vat_number or "",
                        c.city or "",
                        c.contact_type or "",
                    ]
                )
            )
            return BuiltSearchDocument(
                organization_id=organization_id,
                resource_type=self.resource_type,
                resource_id=f"contact:{c.id}",
                resource_version=resource_version,
                title=title[:512],
                subtitle=c.city,
                content=None,
                search_text=search_text,
                status=c.status,
                category=SearchCategories.CONTACT,
            document_date=getattr(c, "updated_at", None) or getattr(c, "created_at", None),
            amount=None,
            currency=None,
            action_url=assert_action_url("/clients"),
            metadata=filter_metadata(
                {
                    "contact_type": c.contact_type,
                    "siret": c.siret,
                    "vat_number": c.vat_number,
                    "city": c.city,
                    "email": c.email,
                }
            ),
            content_hash=content_hash(title, search_text),
        )
        cust: Customer = obj
        title = cust.name or f"Client {cust.id}"
        search_text = sanitize_indexed_text(
            "\n".join([title, cust.email or "", cust.vat_number or ""])
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(cust.id),
            resource_version=resource_version,
            title=title[:512],
            subtitle=None,
            content=None,
            search_text=search_text,
            status=None,
            category=SearchCategories.CONTACT,
            document_date=getattr(cust, "created_at", None),
            amount=None,
            currency=None,
            action_url=assert_action_url("/clients"),
            metadata=filter_metadata({"email": cust.email, "vat_number": cust.vat_number}),
            content_hash=content_hash(title, search_text),
        )


class SupplierIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SUPPLIER

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Contact:
        cid = int(str(resource_id).replace("contact:", ""))
        row = db.query(Contact).filter(Contact.id == cid).first()
        if not row or row.organization_id != organization_id:
            raise SearchNotFoundError("Fournisseur introuvable")
        if row.contact_type not in ("supplier", "customer_and_supplier"):
            raise SearchNotFoundError("Contact non fournisseur")
        return row

    def build_search_document(
        self,
        resource: Contact,
        *,
        organization_id: int,
        resource_version: int = 1,
    ) -> BuiltSearchDocument:
        title = _contact_display_name(resource)
        search_text = sanitize_indexed_text(
            "\n".join(
                [
                    title,
                    resource.email or "",
                    resource.phone or "",
                    resource.siret or "",
                    resource.vat_number or "",
                    resource.city or "",
                    "supplier",
                ]
            )
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=f"contact:{resource.id}",
            resource_version=resource_version,
            title=title[:512],
            subtitle=resource.city,
            content=None,
            search_text=search_text,
            status=resource.status,
            category=SearchCategories.CONTACT,
            document_date=getattr(resource, "updated_at", None)
            or getattr(resource, "created_at", None),
            amount=None,
            currency=None,
            action_url=assert_action_url("/clients"),
            metadata=filter_metadata(
                {
                    "contact_type": resource.contact_type,
                    "siret": resource.siret,
                    "vat_number": resource.vat_number,
                    "city": resource.city,
                    "email": resource.email,
                }
            ),
            content_hash=content_hash(title, search_text),
        )
