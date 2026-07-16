from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import (
    ai,
    auth,
    billing,
    dashboard,
    documents,
    elfis_ai,
    exports,
    modules,
    org,
    platform,
    settings as settings_router,
    subscriptions,
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
    version="0.8.0",
    lifespan=lifespan,
)

DEFAULT_CORS_ORIGINS = [
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


def _cors_headers_for(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin") or ""
    allowed = cors_kwargs.get("allow_origins") or []
    headers: dict[str, str] = {
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    if allowed == ["*"]:
        headers["Access-Control-Allow-Origin"] = "*"
        return headers
    if origin and (origin in allowed or origin in DEFAULT_CORS_ORIGINS):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
        return headers
    # Fallback prod front
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
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
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
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
app.include_router(subscriptions.router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(elfis_ai.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(modules.router, prefix="/api")


@app.get("/api/health")
def health():
    ai_mode = "openai" if settings.openai_api_key else "guided"
    firebase_ok = bool(settings.firebase_web_api_key and settings.firebase_project_id)
    stripe_ok = bool(settings.stripe_secret_key and settings.stripe_price_pro)
    return {
        "status": "ok",
        "app": settings.app_name,
        "product": settings.product_name,
        "ai_mode": ai_mode,
        "details": {
            "slogan": "Déposez une facture. L'IA prépare votre comptabilité.",
            "version": "0.8.0",
            "modules_live": [
                "comptabilite",
                "banque",
                "tresorerie",
                "facturation",
                "auth",
                "assistant",
                "pilotage",
                "subscriptions",
                "elfis_ai",
            ],
            "auth": "firebase",
            "firebase_configured": firebase_ok,
            "firebase_project_id": settings.firebase_project_id or None,
            "auth_required": settings.auth_required,
            "stripe_configured": stripe_ok,
            "stripe_webhook_configured": bool(settings.stripe_webhook_secret),
            "frontend_url": settings.frontend_url,
            "stack_note": "ELFIS Core FastAPI + Firebase Auth + Firestore (multi-tenant)",
        },
    }
