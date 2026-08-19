"""Search indexers — SalesPilot CRM entities."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.sales_crm.models import (
    SalesActivity,
    SalesCompany,
    SalesLead,
    SalesOpportunity,
    SalesPerson,
    SalesTask,
)
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


def _alive(row: Any) -> bool:
    return getattr(row, "deleted_at", None) is None


class SalesLeadIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_LEAD

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = db.query(SalesLead).filter(SalesLead.id == int(resource_id)).first()
        if not row or row.organization_id != organization_id or not _alive(row):
            raise SearchNotFoundError("Lead introuvable")
        return row

    def build_search_document(
        self, resource: Any, *, organization_id: int, resource_version: int = 1, **kwargs: Any
    ) -> BuiltSearchDocument:
        r: SalesLead = resource
        title = r.title
        text = sanitize_indexed_text(
            "\n".join(
                [
                    title,
                    r.company_name or "",
                    r.contact_name or "",
                    r.email or "",
                    r.phone or "",
                    r.source or "",
                    r.status or "",
                    r.description or "",
                ]
            )
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=title,
            subtitle=r.company_name,
            category=SearchCategories.SALES,
            search_text=text,
            content_hash=content_hash(title, text),
            metadata=filter_metadata(
                {"status": r.status, "priority": r.priority, "owner_user_id": r.owner_user_id}
            ),
            action_url=assert_action_url(f"/sales/workspace/lead/{r.id}"),
        )


class SalesCompanyIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_COMPANY

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = db.query(SalesCompany).filter(SalesCompany.id == int(resource_id)).first()
        if not row or row.organization_id != organization_id or not _alive(row):
            raise SearchNotFoundError("Company introuvable")
        return row

    def build_search_document(
        self, resource: Any, *, organization_id: int, resource_version: int = 1, **kwargs: Any
    ) -> BuiltSearchDocument:
        r: SalesCompany = resource
        text = sanitize_indexed_text(
            "\n".join([r.name, r.trade_name or "", r.email or "", r.city or "", r.siret or ""])
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=r.name,
            subtitle=r.city,
            category=SearchCategories.SALES,
            search_text=text,
            content_hash=content_hash(r.name, text),
            metadata=filter_metadata({"status": r.status}),
            action_url=assert_action_url(f"/sales/workspace/company/{r.id}"),
        )


class SalesPersonIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_PERSON

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = db.query(SalesPerson).filter(SalesPerson.id == int(resource_id)).first()
        if not row or row.organization_id != organization_id or not _alive(row):
            raise SearchNotFoundError("Person introuvable")
        return row

    def build_search_document(
        self, resource: Any, *, organization_id: int, resource_version: int = 1, **kwargs: Any
    ) -> BuiltSearchDocument:
        r: SalesPerson = resource
        title = f"{r.first_name} {r.last_name}".strip()
        text = sanitize_indexed_text("\n".join([title, r.email or "", r.phone or "", r.job_title or ""]))
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=title,
            subtitle=r.job_title,
            category=SearchCategories.SALES,
            search_text=text,
            content_hash=content_hash(title, text),
            metadata=filter_metadata({"company_id": r.company_id}),
            action_url=assert_action_url(f"/sales/workspace/person/{r.id}"),
        )


class SalesOpportunityIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_OPPORTUNITY

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = db.query(SalesOpportunity).filter(SalesOpportunity.id == int(resource_id)).first()
        if not row or row.organization_id != organization_id or not _alive(row):
            raise SearchNotFoundError("Opportunity introuvable")
        return row

    def build_search_document(
        self, resource: Any, *, organization_id: int, resource_version: int = 1, **kwargs: Any
    ) -> BuiltSearchDocument:
        r: SalesOpportunity = resource
        amount = str(r.estimated_amount) if r.estimated_amount is not None else ""
        text = sanitize_indexed_text("\n".join([r.name, r.source or "", r.status or "", amount, r.description or ""]))
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=r.name,
            subtitle=amount or r.status,
            category=SearchCategories.SALES,
            search_text=text,
            amount=float(r.estimated_amount) if r.estimated_amount is not None else None,
            metadata=filter_metadata(
                {
                    "status": r.status,
                    "pipeline_id": r.pipeline_id,
                    "stage_id": r.stage_id,
                    "probability": r.probability,
                }
            ),
            action_url=assert_action_url(f"/sales/deals/{r.id}"),
            content_hash=content_hash(r.name, text),
        )


class SalesTaskIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_TASK

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = db.query(SalesTask).filter(SalesTask.id == int(resource_id)).first()
        if not row or row.organization_id != organization_id or not _alive(row):
            raise SearchNotFoundError("Task introuvable")
        return row

    def build_search_document(
        self, resource: Any, *, organization_id: int, resource_version: int = 1, **kwargs: Any
    ) -> BuiltSearchDocument:
        r: SalesTask = resource
        text = sanitize_indexed_text("\n".join([r.title, r.description or "", r.status or ""]))
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=r.title,
            subtitle=r.status,
            category=SearchCategories.SALES,
            search_text=text,
            content_hash=content_hash(r.title, text),
            metadata=filter_metadata({"status": r.status, "priority": r.priority}),
            action_url=assert_action_url(f"/sales/tasks?id={r.id}"),
        )


class SalesActivityIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_ACTIVITY

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = db.query(SalesActivity).filter(SalesActivity.id == int(resource_id)).first()
        if not row or row.organization_id != organization_id or not _alive(row):
            raise SearchNotFoundError("Activity introuvable")
        return row

    def build_search_document(
        self, resource: Any, *, organization_id: int, resource_version: int = 1, **kwargs: Any
    ) -> BuiltSearchDocument:
        r: SalesActivity = resource
        text = sanitize_indexed_text(
            "\n".join([r.subject, r.activity_type or "", r.result or "", r.comment or ""])
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=r.subject,
            subtitle=r.activity_type,
            category=SearchCategories.SALES,
            search_text=text,
            content_hash=content_hash(r.subject, text),
            metadata=filter_metadata({"activity_type": r.activity_type}),
            action_url=assert_action_url(f"/sales/activities?id={r.id}"),
        )
