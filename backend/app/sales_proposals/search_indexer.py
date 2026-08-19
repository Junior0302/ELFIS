"""Search indexer — CommercialProposal (S1.6)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.sales_crm.models import SalesCompany, SalesOpportunity
from app.sales_proposals.models import CommercialProposal
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


class SalesProposalIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.SALES_PROPOSAL

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        row = (
            db.query(CommercialProposal)
            .filter(
                CommercialProposal.id == int(resource_id),
                CommercialProposal.organization_id == organization_id,
            )
            .first()
        )
        if not row or row.deleted_at is not None:
            raise SearchNotFoundError("Proposition introuvable")
        company_name = ""
        if row.sales_company_id:
            c = db.get(SalesCompany, row.sales_company_id)
            if c:
                company_name = c.name or ""
        opp_name = ""
        if row.opportunity_id:
            o = db.get(SalesOpportunity, row.opportunity_id)
            if o:
                opp_name = o.name or ""
        return {"proposal": row, "company_name": company_name, "opp_name": opp_name}

    def build_search_document(
        self,
        resource: Any,
        *,
        organization_id: int,
        resource_version: int = 1,
        **kwargs: Any,
    ) -> BuiltSearchDocument:
        r: CommercialProposal = resource["proposal"]
        company_name = resource.get("company_name") or ""
        opp_name = resource.get("opp_name") or ""
        text = sanitize_indexed_text(
            "\n".join([r.proposal_number, company_name, opp_name, r.status, r.proposal_type])
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(r.id),
            resource_version=resource_version,
            title=r.proposal_number,
            subtitle=company_name or r.status,
            category=SearchCategories.SALES,
            search_text=text,
            amount=None,
            metadata=filter_metadata(
                {
                    "status": r.status,
                    "proposal_type": r.proposal_type,
                    "opportunity_id": r.opportunity_id,
                    "linked_customer_id": r.linked_customer_id,
                    "linked_invoice_id": r.linked_invoice_id,
                }
            ),
            action_url=assert_action_url(f"/sales/proposals/{r.id}"),
            content_hash=content_hash(
                r.proposal_number, text, str(r.linked_invoice_id or "")
            ),
        )
