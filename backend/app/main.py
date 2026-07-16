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
    version="0.7.5",
    lifespan=lifespan,
)

cors_kwargs: dict = {
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.cors_origin_list == ["*"]:
    cors_kwargs["allow_origins"] = ["*"]
    cors_kwargs["allow_credentials"] = False
else:
    cors_kwargs["allow_origins"] = settings.cors_origin_list
    cors_kwargs["allow_credentials"] = True

app.add_middleware(CORSMiddleware, **cors_kwargs)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
        raise exc
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "internal_error",
                "message": "Erreur serveur inattendue",
            }
        },
    )


app.include_router(auth.router, prefix="/api")
app.include_router(org.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
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
            "version": "0.7.5",
            "modules_live": [
                "comptabilite",
                "banque",
                "tresorerie",
                "facturation",
                "auth",
                "assistant",
                "pilotage",
                "subscriptions",
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
