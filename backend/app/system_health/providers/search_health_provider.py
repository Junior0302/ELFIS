"""Provider réel — Search (schéma + index GIN, lecture seule)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_thresholds import HealthThresholds, load_thresholds
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)

SEARCH_TABLE = "elfis_search_documents"
SEARCH_VECTOR_COLUMN = "search_vector"
GIN_INDEX_NAME = "ix_elfis_search_vector_gin"


def _default_session_factory() -> Session:
    from app.database import SessionLocal

    return SessionLocal()


class SearchHealthProvider(HealthProvider):
    service_id = "search"
    service_name = "Search"
    category = HealthCategory.SEARCH.value

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        thresholds: HealthThresholds | None = None,
        timeout_seconds: float | None = None,
        # Hooks de test pour forcer l'état schéma
        schema_inspector: Callable[[Session], dict[str, Any]] | None = None,
    ) -> None:
        self._session_factory = session_factory or _default_session_factory
        self._thresholds = thresholds or load_thresholds()
        self._timeout = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else self._thresholds.provider_timeout_seconds
        )
        self._schema_inspector = schema_inspector

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=self._timeout, label=self.service_id)
        except Exception as exc:
            logger.warning("system_health_search_failed", extra={"error": type(exc).__name__})
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Search inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="search_check_failed",
                error_message=safe_error_message(exc),
            )

    def _inspect_schema(self, db: Session) -> dict[str, Any]:
        if self._schema_inspector is not None:
            return self._schema_inspector(db)

        dialect = getattr(db.bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "unknown") if dialect else "unknown"
        insp = inspect(db.bind)

        table_exists = insp.has_table(SEARCH_TABLE)
        column_exists = False
        column_type: str | None = None
        index_exists = False

        if table_exists:
            cols = {c["name"]: c for c in insp.get_columns(SEARCH_TABLE)}
            column_exists = SEARCH_VECTOR_COLUMN in cols
            if column_exists:
                col = cols[SEARCH_VECTOR_COLUMN]
                raw_type = col.get("type")
                column_type = str(raw_type) if raw_type is not None else None

            if dialect_name == "postgresql":
                try:
                    row = db.execute(
                        text(
                            """
                            SELECT udt_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = :table
                              AND column_name = :col
                            """
                        ),
                        {"table": SEARCH_TABLE, "col": SEARCH_VECTOR_COLUMN},
                    ).fetchone()
                    if row:
                        column_type = str(row[0])
                except Exception:
                    pass
                try:
                    idx = db.execute(
                        text(
                            """
                            SELECT 1
                            FROM pg_indexes
                            WHERE schemaname = 'public'
                              AND indexname = :idx
                            LIMIT 1
                            """
                        ),
                        {"idx": GIN_INDEX_NAME},
                    ).fetchone()
                    index_exists = idx is not None
                except Exception:
                    index_exists = False
            else:
                # Hors PostgreSQL : pas d'index GIN attendu
                index_exists = False

        return {
            "dialect": dialect_name,
            "table_exists": table_exists,
            "column_exists": column_exists,
            "column_type": column_type,
            "index_exists": index_exists,
        }

    def _check(self) -> HealthCheckResult:
        db = self._session_factory()
        try:
            t0 = time.perf_counter()
            info = self._inspect_schema(db)
            dialect_name = info["dialect"]
            table_exists = bool(info["table_exists"])
            column_exists = bool(info["column_exists"])
            column_type = info.get("column_type")
            index_exists = bool(info["index_exists"])

            status = HealthStatus.HEALTHY
            summary = "Index Search disponible"
            error_code = None
            error_message = None
            recommendation = None
            indexed_docs: int | None = None
            query_ok = False

            if not table_exists:
                status = HealthStatus.UNHEALTHY
                summary = f"Table {SEARCH_TABLE} absente"
                error_code = "search_table_missing"
                error_message = "Exécuter les migrations Search (sans auto-création ici)"
            elif not column_exists:
                status = HealthStatus.UNHEALTHY
                summary = f"Colonne {SEARCH_VECTOR_COLUMN} absente"
                error_code = "search_vector_missing"
                error_message = "Colonne search_vector manquante — migration Search requise"
            else:
                # Type tsvector attendu sur PostgreSQL
                if dialect_name == "postgresql":
                    type_ok = column_type is not None and "tsvector" in str(column_type).lower()
                    if not type_ok:
                        status = HealthStatus.UNHEALTHY
                        summary = f"Type {SEARCH_VECTOR_COLUMN} incorrect ({column_type})"
                        error_code = "search_vector_wrong_type"
                        error_message = "Attendu: tsvector. Ne pas altérer le schéma depuis le provider."
                    elif not index_exists:
                        status = HealthStatus.DEGRADED
                        summary = f"Index GIN {GIN_INDEX_NAME} absent"
                        error_code = "search_gin_missing"
                        error_message = "Index GIN manquant"
                        recommendation = (
                            f"Créer l'index {GIN_INDEX_NAME} via migration SQL "
                            "(le provider ne crée jamais l'index automatiquement)."
                        )
                else:
                    # SQLite / tests : table + colonne = degraded informatif
                    status = HealthStatus.DEGRADED
                    summary = "Search OK hors PostgreSQL (pas d'index GIN)"
                    error_code = "search_non_postgres"
                    error_message = "Contrôle GIN/tsvector applicable uniquement sur PostgreSQL"

                # Requête minimale légère
                if status != HealthStatus.UNHEALTHY:
                    try:
                        indexed_docs = int(
                            db.execute(
                                text(
                                    f"SELECT count(*) FROM {SEARCH_TABLE} WHERE is_active = true"
                                )
                            ).scalar()
                            or 0
                        )
                        if dialect_name == "postgresql":
                            try:
                                db.execute(
                                    text(
                                        f"""
                                        SELECT search_document_id
                                        FROM {SEARCH_TABLE}
                                        WHERE is_active = true
                                          AND search_vector @@ plainto_tsquery('simple', 'elfis')
                                        LIMIT 1
                                        """
                                    )
                                )
                                query_ok = True
                            except Exception as exc:
                                # Schéma OK mais requête FTS indisponible → degraded sans écraser un code plus précis
                                if status == HealthStatus.HEALTHY:
                                    status = HealthStatus.DEGRADED
                                    summary = "Index présent — requête FTS minimale en échec"
                                    error_code = error_code or "search_query_failed"
                                    error_message = safe_error_message(exc)
                        else:
                            query_ok = True
                    except Exception as exc:
                        if status != HealthStatus.UNHEALTHY:
                            status = HealthStatus.DEGRADED
                        error_code = error_code or "search_query_failed"
                        error_message = safe_error_message(exc)
                        summary = "Schéma Search partiel — requête minimale en échec"

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            metrics = [
                metric("indexed_docs", "Documents indexés", indexed_docs, unit="docs"),
                metric("table_exists", "Table présente", "true" if table_exists else "false"),
                metric("column_exists", "Colonne search_vector", "true" if column_exists else "false"),
                metric("column_type", "Type search_vector", column_type),
                metric("gin_index", "Index GIN", "true" if index_exists else "false"),
                metric("query_ok", "Requête minimale", "true" if query_ok else "false"),
                metric("query_latency_ms", "Latence contrôle", latency_ms, unit="ms", status=status.value),
            ]

            meta: dict[str, Any] = {
                "provider_mode": "real",
                "simulated": False,
                "dialect": dialect_name,
                "table_exists": table_exists,
                "column_exists": column_exists,
                "column_type": column_type,
                "index_exists": index_exists,
                "query_ok": query_ok,
            }
            if recommendation:
                meta["recommendation"] = recommendation

            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=status,
                summary=summary,
                latency_ms=latency_ms,
                checked_at=utcnow(),
                version="v1",
                metrics=metrics,
                metadata=meta,
                error_code=error_code,
                error_message=error_message,
            )
        finally:
            db.close()
