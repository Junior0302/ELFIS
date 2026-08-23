from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import SessionLocal, init_db
from app.middleware.security import SecurityHeadersMiddleware
from app.security.cors_policy import resolve_cors_allow_origins
from app.routers import (
    accounting,
    admin_audit,
    admin_iam,
    admin_storage,
    admin_system_health,
    ai,
    auth,
    billing,
    contacts,
    dashboard,
    document_intelligence,
    document_registry,
    documents,
    elfis_ai,
    email_connections,
    exports,
    fiscal,
    jobs,
    modules,
    notifications,
    observability,
    org,
    org_email,
    platform,
    professional_emails,
    saas_billing,
    shared_relations,
    search,
    security_admin,
    settings as settings_router,
    subscriptions,
    vault,
    webhooks_brevo,
    platform_admin,
    developer_cockpit,
    dev_tools,
)
from app.workspace_provisioning.router import router as workspace_provisioning_router
from app.sales_crm.router import router as sales_crm_router
from app.sales_proposals.router import router as sales_proposals_router
from app.sales_intelligence.router import router as sales_intelligence_router
from app.sales_operations.router import router as sales_operations_router
from app.sales_collaboration.router import router as sales_collaboration_router
from app.dashboard_launch.router import router as dashboard_launch_router
from app.dashboard_command_center.router import router as dashboard_command_center_router
from app.decision_center.router import router as decision_center_router
from app.work_queue.router import router as work_queue_router
from app.document_processing import api as document_processing_api
from app.product_integrations import api as product_integrations_api
from app.migration_center import api as migration_center_api
from app.document_intake.api import routes as document_intake_api
from app.document_analysis.api import routes as document_analysis_api
from app.document_extraction.api import routes as document_extraction_api
from app.validation_mapping.api import routes as validation_mapping_api
from app.import_engine.api import routes as import_engine_api
from app.smart_migration.api import routes as smart_migration_api
from app.accounting_engine.api import routes as accounting_engine_api
from app.accounting_intelligence.api import routes as accounting_intelligence_api
from app.banking.api import routes as banking_api
from app.financial.api import routes as financial_api
from app.services.auth import seed_auth
from app.services.banking import purge_demo_finance_data
from app.security.security_config import is_production


_docs_kwargs: dict = {}
if is_production():
    _docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.observability.structured_logging import configure_structured_logging
    from app.reliability.shutdown_service import run_shutdown
    from app.security.security_startup import assert_startup_configuration

    configure_structured_logging()
    assert_startup_configuration()

    settings.storage_path.mkdir(parents=True, exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        seed_auth(db)
        purge_demo_finance_data(db)
    finally:
        db.close()

    from app.events import bootstrap_handlers
    from app.jobs import bootstrap_job_handlers
    from app.ai import bootstrap_ai_tasks

    bootstrap_handlers()
    bootstrap_job_handlers()
    bootstrap_ai_tasks()

    worker_stop = None
    worker_thread = None
    job_worker_stop = None
    job_worker_thread = None
    from app.security.security_config import is_production as _is_production_runtime

    if settings.elfis_event_worker_enabled and not _is_production_runtime():
        # Mode local optionnel uniquement — en prod : processus séparé
        import threading

        from app.events.event_worker import EventWorker, default_worker_id

        worker_stop = threading.Event()
        worker_id = default_worker_id()

        def _local_worker_loop() -> None:
            while not worker_stop.is_set():
                session = SessionLocal()
                try:
                    EventWorker(session, worker_id=worker_id).process_next_batch()
                except Exception:
                    pass
                finally:
                    session.close()
                worker_stop.wait(settings.elfis_event_worker_poll_interval_seconds)

        worker_thread = threading.Thread(
            target=_local_worker_loop,
            name="elfis-event-worker-local",
            daemon=True,
        )
        worker_thread.start()

    if settings.elfis_job_worker_enabled and not _is_production_runtime():
        import threading

        from app.jobs.job_worker import JobWorker, default_job_worker_id, parse_queues

        job_worker_stop = threading.Event()
        job_wid = default_job_worker_id()
        job_queues = parse_queues()

        def _local_job_worker_loop() -> None:
            while not job_worker_stop.is_set():
                session = SessionLocal()
                try:
                    JobWorker(
                        session, worker_id=job_wid, queues=job_queues
                    ).process_next_batch()
                except Exception:
                    pass
                finally:
                    session.close()
                job_worker_stop.wait(settings.elfis_job_worker_poll_interval_seconds)

        job_worker_thread = threading.Thread(
            target=_local_job_worker_loop,
            name="elfis-job-worker-local",
            daemon=True,
        )
        job_worker_thread.start()

    yield

    if worker_stop is not None:
        worker_stop.set()
    if worker_thread is not None:
        worker_thread.join(timeout=5)
    if job_worker_stop is not None:
        job_worker_stop.set()
    if job_worker_thread is not None:
        job_worker_thread.join(timeout=5)
    run_shutdown()


app = FastAPI(
    title="ELFIS Core API",
    description="Moteur IA commun — ComptaPilot IA (AI Finance Copilot)",
    version="0.8.9",
    lifespan=lifespan,
    **_docs_kwargs,
)

_cors_allow_origins = resolve_cors_allow_origins(
    cors_origins=settings.cors_origins,
    frontend_url=settings.frontend_url,
    production=is_production(),
)

cors_kwargs: dict = {
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["*"],
    "allow_origins": _cors_allow_origins,
    "allow_credentials": _cors_allow_origins != ["*"],
}

app.add_middleware(CORSMiddleware, **cors_kwargs)
app.add_middleware(SecurityHeadersMiddleware)


def _cors_headers_for(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin") or ""
    allowed = list(cors_kwargs.get("allow_origins") or [])
    headers: dict[str, str] = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Organization-Id, X-Requested-With",
    }
    if allowed == ["*"]:
        headers["Access-Control-Allow-Origin"] = "*"
        return headers
    if origin and origin in allowed:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
        return headers
    # Ne jamais refléter une origine inconnue (anti CSRF / data exfil).
    return headers


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    from app.observability.request_context import get_correlation_id, get_request_id
    from app.security.security_exceptions import http_exception_to_body

    rid = getattr(request.state, "request_id", None) or get_request_id()
    cid = getattr(request.state, "correlation_id", None) or get_correlation_id() or rid
    body = http_exception_to_body(exc, request_id=rid, correlation_id=cid)
    headers = _cors_headers_for(request)
    if rid:
        headers["X-Request-Id"] = rid
    if cid:
        headers["X-Correlation-Id"] = cid
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    from app.observability.request_context import get_correlation_id, get_request_id
    from app.security.security_exceptions import build_error_body
    from app.security.security_types import ErrorCode

    rid = getattr(request.state, "request_id", None) or get_request_id()
    cid = getattr(request.state, "correlation_id", None) or get_correlation_id() or rid
    if settings.app_env.lower() == "production":
        legacy: object = {"code": ErrorCode.VALIDATION_ERROR, "message": "Requête invalide"}
        details = {}
    else:
        legacy = exc.errors()
        details = {"errors": exc.errors()}
    body = build_error_body(
        code=ErrorCode.VALIDATION_ERROR,
        message="Requête invalide",
        request_id=rid,
        correlation_id=cid,
        details=details if settings.app_env.lower() != "production" else {},
        legacy_detail=legacy,
    )
    headers = _cors_headers_for(request)
    if rid:
        headers["X-Request-Id"] = rid
    if cid:
        headers["X-Correlation-Id"] = cid
    return JSONResponse(status_code=422, content=body, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    from app.observability.error_reporting import report_error
    from app.observability.request_context import get_correlation_id, get_request_id
    from app.security.security_exceptions import build_error_body
    from app.security.security_types import ErrorCode

    rid = getattr(request.state, "request_id", None) or get_request_id()
    cid = getattr(request.state, "correlation_id", None) or get_correlation_id() or rid
    report_error(exc, error_code=ErrorCode.INTERNAL_ERROR)
    body = build_error_body(
        code=ErrorCode.INTERNAL_ERROR,
        message="Erreur serveur inattendue",
        request_id=rid,
        correlation_id=cid,
        legacy_detail={"code": ErrorCode.INTERNAL_ERROR, "message": "Erreur serveur inattendue"},
    )
    headers = _cors_headers_for(request)
    if rid:
        headers["X-Request-Id"] = rid
    if cid:
        headers["X-Correlation-Id"] = cid
    return JSONResponse(status_code=500, content=body, headers=headers)


app.include_router(auth.router, prefix="/api")
app.include_router(org.router, prefix="/api")
app.include_router(org_email.router, prefix="/api")
app.include_router(email_connections.router, prefix="/api")
app.include_router(professional_emails.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(subscriptions.webhook_alias_router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(platform_admin.router, prefix="/api")
app.include_router(developer_cockpit.router, prefix="/api")
app.include_router(dev_tools.router, prefix="/api")
app.include_router(workspace_provisioning_router, prefix="/api")
app.include_router(security_admin.router, prefix="/api")
app.include_router(admin_system_health.router, prefix="/api")
app.include_router(admin_storage.router, prefix="/api")
app.include_router(admin_iam.router, prefix="/api")
app.include_router(admin_audit.router, prefix="/api")
app.include_router(observability.router, prefix="/api")
# SaaS Billing V2 avant facturation commerciale : /billing/overview = Entitlement Engine
app.include_router(saas_billing.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(webhooks_brevo.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(document_intelligence.router, prefix="/api")
app.include_router(document_intelligence.platform_router, prefix="/api")
app.include_router(accounting.router, prefix="/api")
app.include_router(accounting.platform_router, prefix="/api")
app.include_router(accounting_engine_api.router, prefix="/api")
app.include_router(accounting_intelligence_api.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(search.platform_router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(document_registry.router, prefix="/api")
app.include_router(document_processing_api.router, prefix="/api")
app.include_router(product_integrations_api.router, prefix="/api")
app.include_router(migration_center_api.router, prefix="/api")
app.include_router(document_intake_api.router, prefix="/api")
app.include_router(document_analysis_api.router, prefix="/api")
app.include_router(document_extraction_api.router, prefix="/api")
app.include_router(validation_mapping_api.router, prefix="/api")
app.include_router(import_engine_api.router, prefix="/api")
app.include_router(smart_migration_api.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(shared_relations.router, prefix="/api")
app.include_router(fiscal.router, prefix="/api")
app.include_router(sales_crm_router, prefix="/api")
app.include_router(sales_proposals_router, prefix="/api")
app.include_router(sales_intelligence_router, prefix="/api")
app.include_router(sales_operations_router, prefix="/api")
app.include_router(sales_collaboration_router, prefix="/api")
app.include_router(elfis_ai.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(dashboard_launch_router, prefix="/api")
app.include_router(dashboard_command_center_router, prefix="/api")
app.include_router(decision_center_router, prefix="/api")
app.include_router(work_queue_router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(banking_api.router, prefix="/api")
app.include_router(banking_api.callback_router, prefix="/api")
app.include_router(banking_api.admin_router, prefix="/api")
app.include_router(financial_api.router, prefix="/api")
app.include_router(financial_api.admin_router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(vault.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")


@app.get("/api/health")
def health():
    """Ping public minimal — aucun diagnostic de secrets ni de mailer."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "product": settings.product_name,
        "version": "0.8.9",
    }
