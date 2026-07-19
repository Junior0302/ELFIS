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
from app.routers import (
    ai,
    auth,
    billing,
    contacts,
    dashboard,
    documents,
    elfis_ai,
    email_connections,
    exports,
    modules,
    org,
    org_email,
    platform,
    settings as settings_router,
    subscriptions,
    webhooks_brevo,
)
from app.services.auth import seed_auth
from app.services.banking import purge_demo_finance_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        seed_auth(db)
        purge_demo_finance_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="ELFIS Core API",
    description="Moteur IA commun — ComptaPilot IA (AI Finance Copilot)",
    version="0.8.4",
    lifespan=lifespan,
)

DEFAULT_CORS_ORIGINS = [
    "https://elfis-core.com",
    "https://www.elfis-core.com",
    "https://elfis-core.web.app",
    "https://elfis-core.firebaseapp.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

cors_kwargs: dict = {
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["*"],
}
if settings.cors_origin_list == ["*"]:
    # En prod Render, on évite "*" + credentials : on liste les origines front.
    if settings.app_env.lower() == "production":
        cors_kwargs["allow_origins"] = list(
            dict.fromkeys([*DEFAULT_CORS_ORIGINS, settings.frontend_url.rstrip("/")])
        )
        cors_kwargs["allow_credentials"] = True
    else:
        cors_kwargs["allow_origins"] = ["*"]
        cors_kwargs["allow_credentials"] = False
else:
    cors_kwargs["allow_origins"] = list(
        dict.fromkeys([*settings.cors_origin_list, *DEFAULT_CORS_ORIGINS])
    )
    cors_kwargs["allow_credentials"] = True

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
    if origin and (origin in allowed or origin in DEFAULT_CORS_ORIGINS):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
        return headers
    # Ne jamais refléter une origine inconnue (anti CSRF / data exfil).
    return headers


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers_for(request),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    detail: object
    if settings.app_env.lower() == "production":
        detail = {"code": "validation_error", "message": "Requête invalide"}
    else:
        detail = exc.errors()
    return JSONResponse(
        status_code=422,
        content={"detail": detail},
        headers=_cors_headers_for(request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "internal_error",
                "message": "Erreur serveur inattendue",
            }
        },
        headers=_cors_headers_for(request),
    )


app.include_router(auth.router, prefix="/api")
app.include_router(org.router, prefix="/api")
app.include_router(org_email.router, prefix="/api")
app.include_router(email_connections.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(subscriptions.webhook_alias_router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(webhooks_brevo.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(elfis_ai.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(modules.router, prefix="/api")


@app.get("/api/health")
def health():
    from app.services.mailer import email_configured, email_transport

    firebase_ok = bool(settings.firebase_web_api_key and settings.firebase_project_id)
    stripe_ok = bool(settings.stripe_secret_key and settings.stripe_price_pro)
    return {
        "status": "ok",
        "app": settings.app_name,
        "product": settings.product_name,
        "details": {
            "slogan": "Déposez une facture. L'IA prépare votre comptabilité.",
            "version": "0.8.4",
            "auth_required": settings.auth_required,
            "billing_ready": stripe_ok,
            "auth_ready": firebase_ok,
            "email_ready": email_configured(),
            "email_transport": email_transport(),
        },
    }
