"""Sales Operations Service — calendar, import, duplicates, bulk, journal, saved views."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.sales_crm.models import (
    SalesActivity,
    SalesCompany,
    SalesLead,
    SalesNote,
    SalesOpportunity,
    SalesPerson,
    SalesTask,
)
from app.sales_crm.service import create_company, create_lead, create_person, soft_alive, soft_delete
from app.sales_operations.models import SalesSavedView
from app.sales_operations.schemas import (
    BulkActionIn,
    BulkActionOut,
    CalendarEventOut,
    CalendarOut,
    DuplicateCandidateOut,
    DuplicateResolveIn,
    DuplicateScanOut,
    ImportCommitIn,
    ImportCommitOut,
    ImportPreviewIn,
    ImportPreviewOut,
    ImportPreviewRow,
    JournalItemOut,
    JournalOut,
    SavedViewCreate,
    SavedViewOut,
    SavedViewUpdate,
)
from app.sales_proposals.models import CommercialProposal
from app.services.contacts.normalize import normalize_company_name, normalize_email


def _now() -> datetime:
    return datetime.utcnow()


class SalesOperationsService:
    def __init__(self, db: Session):
        self.db = db

    # ----- Saved views -----

    def list_saved_views(
        self, *, organization_id: int, user_id: int | None, resource: str | None = None
    ) -> list[SalesSavedView]:
        q = self.db.query(SalesSavedView).filter(
            SalesSavedView.organization_id == organization_id,
            SalesSavedView.deleted_at.is_(None),
        )
        if resource:
            q = q.filter(SalesSavedView.resource == resource)
        if user_id is not None:
            q = q.filter(
                (SalesSavedView.owner_user_id == user_id) | (SalesSavedView.is_shared.is_(True))
            )
        return q.order_by(SalesSavedView.name.asc()).all()

    def create_saved_view(
        self, *, organization_id: int, user_id: int | None, data: SavedViewCreate
    ) -> SalesSavedView:
        if data.is_default:
            self._clear_default(organization_id, user_id, data.resource)
        row = SalesSavedView(
            organization_id=organization_id,
            owner_user_id=user_id,
            resource=data.resource,
            name=data.name.strip(),
            filters=data.filters or {},
            sort=data.sort,
            is_default=data.is_default,
            is_shared=data.is_shared,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def update_saved_view(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        view_id: int,
        data: SavedViewUpdate,
    ) -> SalesSavedView:
        row = self._get_view(organization_id, view_id)
        if data.is_default:
            self._clear_default(organization_id, user_id, row.resource)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        row.updated_at = _now()
        self.db.flush()
        return row

    def delete_saved_view(self, *, organization_id: int, view_id: int) -> None:
        row = self._get_view(organization_id, view_id)
        row.deleted_at = _now()
        self.db.flush()

    def _get_view(self, organization_id: int, view_id: int) -> SalesSavedView:
        row = (
            self.db.query(SalesSavedView)
            .filter(
                SalesSavedView.id == view_id,
                SalesSavedView.organization_id == organization_id,
                SalesSavedView.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(404, detail={"code": "not_found", "message": "Vue introuvable"})
        return row

    def _clear_default(self, organization_id: int, user_id: int | None, resource: str) -> None:
        q = self.db.query(SalesSavedView).filter(
            SalesSavedView.organization_id == organization_id,
            SalesSavedView.resource == resource,
            SalesSavedView.is_default.is_(True),
            SalesSavedView.deleted_at.is_(None),
        )
        if user_id is not None:
            q = q.filter(SalesSavedView.owner_user_id == user_id)
        for row in q.all():
            row.is_default = False

    # ----- Calendar -----

    def build_calendar(
        self,
        *,
        organization_id: int,
        from_date: date,
        to_date: date,
        include_tasks: bool = True,
        include_activities: bool = True,
        include_closings: bool = True,
        include_proposals: bool = True,
    ) -> CalendarOut:
        if to_date < from_date:
            raise HTTPException(400, detail={"code": "invalid_range", "message": "Plage invalide"})
        if (to_date - from_date).days > 92:
            raise HTTPException(400, detail={"code": "range_too_large", "message": "Max 92 jours"})
        start = datetime.combine(from_date, time.min)
        end = datetime.combine(to_date, time.max)
        events: list[CalendarEventOut] = []

        if include_activities:
            acts = (
                soft_alive(self.db.query(SalesActivity), SalesActivity)
                .filter(
                    SalesActivity.organization_id == organization_id,
                    SalesActivity.activity_at >= start,
                    SalesActivity.activity_at <= end,
                )
                .order_by(SalesActivity.activity_at.asc())
                .limit(500)
                .all()
            )
            for a in acts:
                route = f"/sales/deals/{a.opportunity_id}" if a.opportunity_id else "/sales/activities"
                events.append(
                    CalendarEventOut(
                        id=f"activity:{a.id}",
                        event_type=a.activity_type or "activity",
                        title=a.subject or "Activité",
                        starts_at=a.activity_at,
                        source_type="sales_activity",
                        source_id=a.id,
                        route=route,
                        meta={"activity_type": a.activity_type},
                    )
                )

        if include_tasks:
            tasks = (
                soft_alive(self.db.query(SalesTask), SalesTask)
                .filter(
                    SalesTask.organization_id == organization_id,
                    SalesTask.due_at.isnot(None),
                    SalesTask.due_at >= start,
                    SalesTask.due_at <= end,
                )
                .order_by(SalesTask.due_at.asc())
                .limit(500)
                .all()
            )
            for t in tasks:
                route = f"/sales/deals/{t.opportunity_id}" if t.opportunity_id else "/sales/tasks"
                events.append(
                    CalendarEventOut(
                        id=f"task:{t.id}",
                        event_type="task",
                        title=t.title,
                        starts_at=t.due_at,
                        source_type="sales_task",
                        source_id=t.id,
                        route=route,
                        severity="high" if (t.priority or "").lower() == "high" else None,
                        meta={"status": t.status, "priority": t.priority},
                    )
                )

        if include_closings:
            opps = (
                soft_alive(self.db.query(SalesOpportunity), SalesOpportunity)
                .filter(
                    SalesOpportunity.organization_id == organization_id,
                    SalesOpportunity.status == "open",
                    SalesOpportunity.expected_close_date.isnot(None),
                    SalesOpportunity.expected_close_date >= from_date,
                    SalesOpportunity.expected_close_date <= to_date,
                )
                .limit(300)
                .all()
            )
            for o in opps:
                events.append(
                    CalendarEventOut(
                        id=f"closing:{o.id}",
                        event_type="closing",
                        title=f"Closing — {o.name}",
                        starts_at=datetime.combine(o.expected_close_date, time(9, 0)),
                        source_type="sales_opportunity",
                        source_id=o.id,
                        route=f"/sales/deals/{o.id}",
                    )
                )

        if include_proposals:
            props = (
                self.db.query(CommercialProposal)
                .filter(
                    CommercialProposal.organization_id == organization_id,
                    CommercialProposal.deleted_at.is_(None),
                    CommercialProposal.valid_until.isnot(None),
                    CommercialProposal.valid_until >= from_date,
                    CommercialProposal.valid_until <= to_date,
                )
                .limit(200)
                .all()
            )
            for p in props:
                events.append(
                    CalendarEventOut(
                        id=f"proposal:{p.id}",
                        event_type="proposal_expiry",
                        title=f"Expiration — {p.proposal_number}",
                        starts_at=datetime.combine(p.valid_until, time(18, 0)),
                        source_type="sales_proposal",
                        source_id=p.id,
                        route=f"/sales/proposals/{p.id}",
                        meta={"status": p.status},
                    )
                )

        events.sort(key=lambda e: e.starts_at)
        return CalendarOut(
            events=events, from_date=from_date, to_date=to_date, generated_at=_now()
        )

    # ----- Import -----

    def preview_import(
        self, *, organization_id: int, data: ImportPreviewIn
    ) -> ImportPreviewOut:
        reader = csv.DictReader(io.StringIO(data.csv_text), delimiter=data.delimiter or ",")
        if not reader.fieldnames:
            raise HTTPException(400, detail={"code": "no_columns", "message": "CSV sans colonnes"})
        columns = [c.strip() for c in reader.fieldnames if c]
        mapping = self._map_columns(data.resource, columns)
        rows_out: list[ImportPreviewRow] = []
        ok = err = dup = 0
        for i, raw in enumerate(reader, start=2):
            if i > 502:
                break
            mapped = {dst: (raw.get(src) or "").strip() for dst, src in mapping.items() if src in raw}
            messages: list[str] = []
            status: str = "ok"
            dup_id = None
            if data.resource == "leads" and not mapped.get("title"):
                status = "error"
                messages.append("title requis")
            elif data.resource == "companies" and not mapped.get("name"):
                status = "error"
                messages.append("name requis")
            elif data.resource == "people" and (
                not mapped.get("first_name") or not mapped.get("last_name")
            ):
                status = "error"
                messages.append("first_name et last_name requis")
            else:
                dup_id = self._find_import_duplicate(organization_id, data.resource, mapped)
                if dup_id:
                    status = "duplicate"
                    messages.append(f"Doublon possible #{dup_id}")
                    dup += 1
            if status == "ok":
                ok += 1
            elif status == "error":
                err += 1
            rows_out.append(
                ImportPreviewRow(
                    row_number=i,
                    data=mapped,
                    status=status,  # type: ignore[arg-type]
                    messages=messages,
                    duplicate_of_id=dup_id,
                )
            )
        return ImportPreviewOut(
            resource=data.resource,
            columns_detected=columns,
            column_mapping={k: v for k, v in mapping.items()},
            rows=rows_out,
            ok_count=ok,
            error_count=err,
            duplicate_count=dup,
        )

    def commit_import(
        self, *, organization_id: int, user_id: int | None, data: ImportCommitIn
    ) -> ImportCommitOut:
        created = skipped = 0
        errors: list[str] = []
        for idx, row in enumerate(data.rows, start=1):
            try:
                if data.skip_duplicates:
                    dup = self._find_import_duplicate(organization_id, data.resource, row)
                    if dup:
                        skipped += 1
                        continue
                if data.resource == "leads":
                    create_lead(self.db, organization_id=organization_id, user_id=user_id, data=row)
                elif data.resource == "companies":
                    create_company(self.db, organization_id=organization_id, user_id=user_id, data=row)
                else:
                    create_person(self.db, organization_id=organization_id, user_id=user_id, data=row)
                created += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Ligne {idx}: {exc}")
        self.db.flush()
        return ImportCommitOut(created=created, skipped=skipped, errors=errors[:50])

    def _map_columns(self, resource: str, columns: list[str]) -> dict[str, str]:
        aliases = {
            "leads": {
                "title": ["title", "titre", "lead", "name", "nom"],
                "email": ["email", "mail", "e-mail"],
                "phone": ["phone", "telephone", "tel", "mobile"],
                "company_name": ["company", "company_name", "entreprise", "societe"],
                "contact_name": ["contact", "contact_name"],
                "source": ["source"],
                "priority": ["priority", "priorite"],
            },
            "companies": {
                "name": ["name", "nom", "company", "raison_sociale"],
                "email": ["email", "mail"],
                "phone": ["phone", "telephone", "tel"],
                "siret": ["siret"],
                "vat_number": ["vat", "vat_number", "tva"],
                "city": ["city", "ville"],
            },
            "people": {
                "first_name": ["first_name", "prenom", "firstname"],
                "last_name": ["last_name", "nom", "lastname"],
                "email": ["email", "mail"],
                "phone": ["phone", "telephone", "tel"],
                "job_title": ["job_title", "titre", "fonction"],
            },
        }
        lower = {c.lower().strip(): c for c in columns}
        mapping: dict[str, str] = {}
        for field, names in aliases.get(resource, {}).items():
            for n in names:
                if n in lower:
                    mapping[field] = lower[n]
                    break
        return mapping

    def _find_import_duplicate(
        self, organization_id: int, resource: str, data: dict[str, Any]
    ) -> int | None:
        email = normalize_email(data.get("email") or "")
        if resource == "companies":
            name = normalize_company_name(data.get("name") or "")
            q = soft_alive(self.db.query(SalesCompany), SalesCompany).filter(
                SalesCompany.organization_id == organization_id
            )
            for c in q.limit(200).all():
                if email and normalize_email(c.email or "") == email:
                    return c.id
                if name and normalize_company_name(c.name or "") == name:
                    return c.id
        elif resource == "people":
            q = soft_alive(self.db.query(SalesPerson), SalesPerson).filter(
                SalesPerson.organization_id == organization_id
            )
            for p in q.limit(200).all():
                if email and normalize_email(p.email or "") == email:
                    return p.id
        else:
            q = soft_alive(self.db.query(SalesLead), SalesLead).filter(
                SalesLead.organization_id == organization_id
            )
            title = (data.get("title") or "").strip().lower()
            for lead in q.limit(200).all():
                if email and normalize_email(lead.email or "") == email:
                    return lead.id
                if title and (lead.title or "").strip().lower() == title:
                    return lead.id
        return None

    # ----- Duplicates -----

    def scan_duplicates(
        self, *, organization_id: int, resource: str, limit: int = 200
    ) -> DuplicateScanOut:
        groups: list[list[DuplicateCandidateOut]] = []
        scanned = 0
        if resource == "companies":
            rows = (
                soft_alive(self.db.query(SalesCompany), SalesCompany)
                .filter(SalesCompany.organization_id == organization_id)
                .limit(limit)
                .all()
            )
            scanned = len(rows)
            by_email: dict[str, list[SalesCompany]] = defaultdict(list)
            by_name: dict[str, list[SalesCompany]] = defaultdict(list)
            for c in rows:
                if c.email:
                    by_email[normalize_email(c.email)].append(c)
                by_name[normalize_company_name(c.name)].append(c)
            seen: set[tuple[int, int]] = set()
            for bucket, level, matched in (
                (by_email, "exact", ["email"]),
                (by_name, "possible", ["name"]),
            ):
                for items in bucket.values():
                    if len(items) < 2:
                        continue
                    key = tuple(sorted(i.id for i in items[:2]))
                    if key in seen:
                        continue
                    seen.add(key)
                    groups.append(
                        [
                            DuplicateCandidateOut(
                                resource="companies",
                                record_id=i.id,
                                label=i.name,
                                match_level=level,  # type: ignore[arg-type]
                                matched_on=matched,
                                record={"id": i.id, "name": i.name, "email": i.email},
                            )
                            for i in items[:5]
                        ]
                    )
        elif resource == "people":
            rows = (
                soft_alive(self.db.query(SalesPerson), SalesPerson)
                .filter(SalesPerson.organization_id == organization_id)
                .limit(limit)
                .all()
            )
            scanned = len(rows)
            by_email: dict[str, list[SalesPerson]] = defaultdict(list)
            for p in rows:
                if p.email:
                    by_email[normalize_email(p.email)].append(p)
            for items in by_email.values():
                if len(items) < 2:
                    continue
                groups.append(
                    [
                        DuplicateCandidateOut(
                            resource="people",
                            record_id=i.id,
                            label=f"{i.first_name} {i.last_name}",
                            match_level="exact",
                            matched_on=["email"],
                            record={
                                "id": i.id,
                                "first_name": i.first_name,
                                "last_name": i.last_name,
                                "email": i.email,
                            },
                        )
                        for i in items[:5]
                    ]
                )
        else:  # leads
            rows = (
                soft_alive(self.db.query(SalesLead), SalesLead)
                .filter(SalesLead.organization_id == organization_id)
                .limit(limit)
                .all()
            )
            scanned = len(rows)
            by_email: dict[str, list[SalesLead]] = defaultdict(list)
            for lead in rows:
                if lead.email:
                    by_email[normalize_email(lead.email)].append(lead)
            for items in by_email.values():
                if len(items) < 2:
                    continue
                groups.append(
                    [
                        DuplicateCandidateOut(
                            resource="leads",
                            record_id=i.id,
                            label=i.title,
                            match_level="exact",
                            matched_on=["email"],
                            record={"id": i.id, "title": i.title, "email": i.email},
                        )
                        for i in items[:5]
                    ]
                )
        return DuplicateScanOut(
            resource=resource, groups=groups[:50], scanned=scanned, generated_at=_now()
        )

    def resolve_duplicate(
        self, *, organization_id: int, user_id: int | None, data: DuplicateResolveIn
    ) -> dict[str, Any]:
        """Never auto-merges. ignore / link / prepare only."""
        if data.action == "manual_merge_prepare":
            return {
                "action": data.action,
                "primary_id": data.primary_id,
                "secondary_id": data.secondary_id,
                "message": "Fusion manuelle à confirmer hors de cette V1 — aucune donnée modifiée.",
                "modified": False,
            }
        if data.action == "ignore":
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.SALES_DUPLICATE_IGNORED,
                    organization_id=organization_id,
                    aggregate_type=data.resource,
                    aggregate_id=str(data.primary_id),
                    payload={
                        "primary_id": data.primary_id,
                        "secondary_id": data.secondary_id,
                        "resource": data.resource,
                    },
                    metadata={"actor_user_id": str(user_id) if user_id else None},
                    idempotency_key=f"sales:dup:ignore:{data.resource}:{data.primary_id}:{data.secondary_id}",
                ),
                commit=False,
            )
            return {"action": "ignore", "modified": False, "message": "Doublon ignoré (journalisé)."}
        # link — store note only, no merge
        return {
            "action": "link",
            "modified": False,
            "message": "Lien manuel enregistré conceptuellement — pas de fusion automatique.",
            "note": data.note,
        }

    # ----- Bulk -----

    def bulk_action(
        self, *, organization_id: int, user_id: int | None, data: BulkActionIn
    ) -> BulkActionOut:
        if not data.confirm:
            raise HTTPException(
                400,
                detail={"code": "confirmation_required", "message": "confirm=true requis"},
            )
        updated = skipped = 0
        errors: list[str] = []
        for rid in data.ids:
            try:
                if data.resource == "tasks" and data.action == "mark_done":
                    row = soft_alive(self.db.query(SalesTask), SalesTask).filter(
                        SalesTask.organization_id == organization_id, SalesTask.id == rid
                    ).first()
                    if not row:
                        skipped += 1
                        continue
                    row.status = "done"
                    row.completed_at = _now()
                    updated += 1
                elif data.action == "soft_delete":
                    model = {
                        "leads": SalesLead,
                        "companies": SalesCompany,
                        "people": SalesPerson,
                        "opportunities": SalesOpportunity,
                        "tasks": SalesTask,
                        "activities": SalesActivity,
                        "notes": SalesNote,
                    }.get(data.resource)
                    if not model:
                        errors.append(f"Resource non supportée: {data.resource}")
                        break
                    row = soft_alive(self.db.query(model), model).filter(
                        model.organization_id == organization_id,
                        model.id == rid,
                    ).first()
                    if not row:
                        skipped += 1
                        continue
                    soft_delete(row, user_id=user_id)
                    updated += 1
                elif data.resource == "opportunities" and data.action == "assign":
                    row = soft_alive(self.db.query(SalesOpportunity), SalesOpportunity).filter(
                        SalesOpportunity.organization_id == organization_id,
                        SalesOpportunity.id == rid,
                    ).first()
                    if not row:
                        skipped += 1
                        continue
                    owner = data.payload.get("owner_user_id")
                    if owner is None:
                        errors.append("owner_user_id requis")
                        break
                    row.owner_user_id = int(owner)
                    updated += 1
                    if int(owner) != user_id:
                        self._notify_ops(
                            organization_id=organization_id,
                            user_id=int(owner),
                            title="Opportunité assignée",
                            message=f"Une opportunité vous a été assignée (#{rid}).",
                            action_url=f"/sales/deals/{rid}",
                            idempotency_key=f"sales:ops:assign:{rid}:{owner}",
                        )
                elif data.resource == "opportunities" and data.action == "change_stage":
                    from app.sales_crm.pipeline_service import SalesPipelineService

                    stage_id = data.payload.get("stage_id")
                    if not stage_id:
                        errors.append("stage_id requis")
                        break
                    SalesPipelineService(self.db).move_stage(
                        organization_id=organization_id,
                        user_id=user_id,
                        opportunity_id=rid,
                        stage_id=int(stage_id),
                    )
                    updated += 1
                else:
                    skipped += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"id={rid}: {exc}")
        self.db.flush()
        return BulkActionOut(updated=updated, skipped=skipped, errors=errors[:30])

    # ----- Journal -----

    def my_activity(
        self, *, organization_id: int, user_id: int | None, limit: int = 50
    ) -> JournalOut:
        items: list[JournalItemOut] = []
        limit = min(100, max(1, limit))
        since = _now() - timedelta(days=30)

        acts = (
            soft_alive(self.db.query(SalesActivity), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.created_at >= since,
            )
            .order_by(SalesActivity.created_at.desc())
            .limit(limit)
            .all()
        )
        for a in acts:
            items.append(
                JournalItemOut(
                    id=f"activity:{a.id}",
                    kind="activity",
                    title=a.subject or a.activity_type,
                    summary=a.result,
                    occurred_at=a.created_at or a.activity_at,
                    source_type="sales_activity",
                    source_id=a.id,
                    route="/sales/activities",
                )
            )

        tasks = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.updated_at >= since,
            )
            .order_by(SalesTask.updated_at.desc())
            .limit(limit)
            .all()
        )
        for t in tasks:
            items.append(
                JournalItemOut(
                    id=f"task:{t.id}",
                    kind="task",
                    title=t.title,
                    summary=t.status,
                    occurred_at=t.updated_at or t.created_at,
                    source_type="sales_task",
                    source_id=t.id,
                    route="/sales/tasks",
                )
            )

        notes = (
            soft_alive(self.db.query(SalesNote), SalesNote)
            .filter(
                SalesNote.organization_id == organization_id,
                SalesNote.created_at >= since,
            )
            .order_by(SalesNote.created_at.desc())
            .limit(limit)
            .all()
        )
        for n in notes:
            items.append(
                JournalItemOut(
                    id=f"note:{n.id}",
                    kind="note",
                    title=f"Note {n.entity_type}#{n.entity_id}",
                    summary=(n.body_markdown or "")[:120],
                    occurred_at=n.created_at,
                    source_type="sales_note",
                    source_id=n.id,
                    route=None,
                )
            )

        props = (
            self.db.query(CommercialProposal)
            .filter(
                CommercialProposal.organization_id == organization_id,
                CommercialProposal.deleted_at.is_(None),
                CommercialProposal.updated_at >= since,
            )
            .order_by(CommercialProposal.updated_at.desc())
            .limit(limit)
            .all()
        )
        for p in props:
            items.append(
                JournalItemOut(
                    id=f"proposal:{p.id}",
                    kind="proposal",
                    title=p.proposal_number,
                    summary=p.status,
                    occurred_at=p.updated_at,
                    source_type="sales_proposal",
                    source_id=p.id,
                    route=f"/sales/proposals/{p.id}",
                )
            )

        items.sort(key=lambda x: x.occurred_at, reverse=True)
        return JournalOut(items=items[:limit], generated_at=_now())

    def _notify_ops(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        title: str,
        message: str,
        action_url: str,
        idempotency_key: str,
    ) -> None:
        if not user_id:
            return
        try:
            from app.notifications.notification_schemas import NotificationRequest
            from app.notifications.notification_service import NotificationService

            NotificationService(self.db).create_notification(
                NotificationRequest(
                    organization_id=organization_id,
                    user_id=user_id,
                    notification_type="sales_ops",
                    category="sales",
                    severity="info",
                    template_name="system_generic",
                    template_data={"title": title, "message": message[:200]},
                    channels=["in_app"],
                    action_url=action_url,
                    action_label="Ouvrir",
                    related_entity_type="sales_ops",
                    related_entity_id=idempotency_key,
                    idempotency_key=idempotency_key,
                )
            )
        except Exception:
            # Never block ops on notification failure
            return
