"""Shared Relations read service — projections only, no table merge."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.models_saas import Contact, Customer
from app.services.shared_relations.adapters import (
    contact_to_shared_relation,
    customer_to_shared_relation,
    sales_company_to_shared_relation,
)
from app.services.shared_relations.contract import (
    SharedRelation,
    SharedRelationDetail,
    SharedRelationListResponse,
    parse_relation_id,
)
from app.services.shared_relations.duplicates import find_duplicates, score_pair

try:
    from app.sales_crm.models import SalesCompany
except Exception:  # pragma: no cover
    SalesCompany = None  # type: ignore


def _load_all(db: Session, organization_id: int) -> list[SharedRelation]:
    items: list[SharedRelation] = []
    customers = (
        db.query(Customer).filter(Customer.organization_id == organization_id).all()
    )
    items.extend(customer_to_shared_relation(c) for c in customers)

    contacts = db.query(Contact).filter(Contact.organization_id == organization_id).all()
    items.extend(contact_to_shared_relation(c) for c in contacts)

    if SalesCompany is not None:
        companies = (
            db.query(SalesCompany)
            .filter(
                SalesCompany.organization_id == organization_id,
                SalesCompany.deleted_at.is_(None),
            )
            .all()
        )
        items.extend(sales_company_to_shared_relation(c) for c in companies)

    items.sort(key=lambda r: (r.display_name or "").lower())
    return items


def _matches_search(rel: SharedRelation, q: str) -> bool:
    needle = q.strip().lower()
    if not needle:
        return True
    hay = " ".join(
        [
            rel.display_name,
            rel.legal_name,
            rel.first_name,
            rel.last_name,
            rel.tax_number,
            rel.siren,
            rel.siret,
            " ".join(rel.emails),
            " ".join(rel.phones),
            " ".join(rel.roles),
            rel.source_system,
        ]
    ).lower()
    return needle in hay


def list_shared_relations(
    db: Session,
    *,
    organization_id: int,
    q: str | None = None,
    role: str | None = None,
    source: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> SharedRelationListResponse:
    items = _load_all(db, organization_id)
    if q:
        items = [r for r in items if _matches_search(r, q)]
    if role:
        role_n = role.strip().lower()
        items = [r for r in items if role_n in r.roles]
    if source:
        source_n = source.strip().lower()
        items = [r for r in items if r.source_system == source_n]
    if status:
        status_n = status.strip().lower()
        items = [r for r in items if r.status == status_n]

    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 50)))
    total = len(items)
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    start = (page - 1) * page_size
    slice_items = items[start : start + page_size]
    return SharedRelationListResponse(
        items=slice_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_shared_relation(
    db: Session, *, organization_id: int, relation_id: str
) -> SharedRelation | None:
    try:
        source, entity_id = parse_relation_id(relation_id)
    except ValueError:
        return None

    if source == "customer":
        row = (
            db.query(Customer)
            .filter(Customer.id == entity_id, Customer.organization_id == organization_id)
            .first()
        )
        return customer_to_shared_relation(row) if row else None
    if source == "contact":
        row = (
            db.query(Contact)
            .filter(Contact.id == entity_id, Contact.organization_id == organization_id)
            .first()
        )
        return contact_to_shared_relation(row) if row else None
    if source == "sales_company" and SalesCompany is not None:
        row = (
            db.query(SalesCompany)
            .filter(
                SalesCompany.id == entity_id,
                SalesCompany.organization_id == organization_id,
                SalesCompany.deleted_at.is_(None),
            )
            .first()
        )
        return sales_company_to_shared_relation(row) if row else None
    return None


def get_shared_relation_detail(
    db: Session, *, organization_id: int, relation_id: str
) -> SharedRelationDetail | None:
    rel = get_shared_relation(db, organization_id=organization_id, relation_id=relation_id)
    if not rel:
        return None
    all_rels = _load_all(db, organization_id)
    dups = []
    for other in all_rels:
        pair = score_pair(rel, other)
        if pair:
            dups.append(pair)
    dups.sort(key=lambda d: d.confidence, reverse=True)

    usages: dict[str, Any] = {
        "comptapilot": "customer" in rel.roles or "supplier" in rel.roles,
        "salespilot": "commercial_account" in rel.roles or "prospect" in rel.roles,
        "source_system": rel.source_system,
        "source_entity_id": rel.source_entity_id,
        "links": rel.links,
    }
    return SharedRelationDetail(
        relation=rel,
        roles=list(rel.roles),
        usages=usages,
        duplicates=dups,
    )


def list_duplicate_candidates(
    db: Session, *, organization_id: int, relation_id: str | None = None
):
    all_rels = _load_all(db, organization_id)
    if relation_id:
        rel = next((r for r in all_rels if r.id == relation_id), None)
        if not rel:
            return []
        out = []
        for other in all_rels:
            pair = score_pair(rel, other)
            if pair:
                out.append(pair)
        return out
    return find_duplicates(all_rels)
