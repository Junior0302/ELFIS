"""Reporting versionné — JSON / CSV / PDF."""

from __future__ import annotations

import base64
import csv
import io
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.import_engine.enums import ImportRunStatus
from app.import_engine.models import ElfisImportRun
from app.smart_migration.dashboard import SmartMigrationDashboard
from app.smart_migration.metrics import SmartMigrationMetrics
from app.smart_migration.models import ElfisSmartMigrationReport, ElfisSmartMigrationRun


class SmartMigrationReporting:
    def __init__(self, db: Session):
        self._db = db
        self._dashboard = SmartMigrationDashboard(db)
        self._metrics = SmartMigrationMetrics(db)

    def generate(
        self,
        run: ElfisSmartMigrationRun,
        *,
        actor_user_id: int | None,
        formats: list[str] | None = None,
    ) -> ElfisSmartMigrationReport:
        formats = formats or ["json", "csv", "pdf"]
        dash = self._dashboard.build(
            organization_id=run.organization_id,
            migration_session_id=run.migration_session_id,
            smart_run=run,
        )
        metrics = self._metrics.collect(
            organization_id=run.organization_id,
            migration_session_id=run.migration_session_id,
            smart_run=run,
        )
        imports = (
            self._db.query(ElfisImportRun)
            .filter(ElfisImportRun.organization_id == run.organization_id)
            .filter(ElfisImportRun.migration_session_id == run.migration_session_id)
            .filter(ElfisImportRun.status == ImportRunStatus.COMPLETED.value)
            .all()
        )
        created: list[Any] = []
        linked: list[Any] = []
        errors: list[Any] = []
        warnings: list[Any] = []
        for r in imports:
            created.extend(list(r.created_objects_json or []))
            linked.extend(list(r.linked_objects_json or []))
            warnings.extend(list(r.warnings_json or []))
            if r.error_message:
                errors.append(
                    {"import_id": r.id, "code": r.error_code, "message": r.error_message}
                )

        prev = (
            self._db.query(ElfisSmartMigrationReport)
            .filter(ElfisSmartMigrationReport.smart_run_id == run.id)
            .order_by(ElfisSmartMigrationReport.version.desc())
            .first()
        )
        version = int(prev.version) + 1 if prev else 1

        body = {
            "summary": {
                "status": run.status,
                "progress_percent": run.progress_percent,
                "documents_total": dash["documents_total"],
                "documents_imported": dash["documents_imported"],
                "documents_failed": dash["documents_failed"],
            },
            "statistics": metrics,
            "created_objects": created,
            "linked_objects": linked,
            "errors": errors,
            "warnings": warnings,
            "duration_ms": (
                int((run.completed_at - run.started_at).total_seconds() * 1000)
                if run.started_at and run.completed_at
                else None
            ),
            "estimated_cost": metrics.get("estimated_cost"),
            "actual_cost": metrics.get("actual_cost"),
            "version": version,
            "user_id": actor_user_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "migration_id": run.migration_session_id,
            "smart_run_id": run.id,
            "correlation_id": run.correlation_id,
        }

        csv_body = None
        if "csv" in formats:
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["metric", "value"])
            for k, v in metrics.items():
                w.writerow([k, v])
            w.writerow([])
            w.writerow(["created_kind", "id", "label"])
            for o in created:
                w.writerow([o.get("kind"), o.get("id"), o.get("label")])
            csv_body = buf.getvalue()

        pdf_body = None
        if "pdf" in formats:
            # PDF minimal texte (pas de dépendance lourde) — contenu auditable
            lines = [
                "%PDF-1.1",
                "Smart Migration Report",
                f"Migration: {run.migration_session_id}",
                f"Version: {version}",
                f"Status: {run.status}",
                f"Imported: {dash['documents_imported']}/{dash['documents_total']}",
                f"Cost est: {metrics.get('estimated_cost')}",
                f"Timestamp: {body['timestamp']}",
                json.dumps(body["summary"], ensure_ascii=False),
            ]
            pdf_body = base64.b64encode("\n".join(lines).encode("utf-8")).decode("ascii")

        report = ElfisSmartMigrationReport(
            id=str(uuid4()),
            organization_id=run.organization_id,
            smart_run_id=run.id,
            migration_session_id=run.migration_session_id,
            version=version,
            format="json",
            summary_json=body["summary"],
            stats_json=metrics,
            created_objects_json=created,
            linked_objects_json=linked,
            errors_json=errors,
            warnings_json=warnings,
            duration_ms=body["duration_ms"],
            estimated_cost=float(metrics.get("estimated_cost") or 0),
            actual_cost=float(metrics.get("actual_cost") or 0),
            body_json=body,
            body_csv=csv_body,
            body_pdf=pdf_body,
            actor_user_id=actor_user_id,
        )
        self._db.add(report)
        self._db.flush()
        return report

    def get_latest(
        self, *, organization_id: int, smart_run_id: str
    ) -> ElfisSmartMigrationReport | None:
        return (
            self._db.query(ElfisSmartMigrationReport)
            .filter(ElfisSmartMigrationReport.organization_id == organization_id)
            .filter(ElfisSmartMigrationReport.smart_run_id == smart_run_id)
            .order_by(ElfisSmartMigrationReport.version.desc())
            .first()
        )
