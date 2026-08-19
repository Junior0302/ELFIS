"""API Product Integrations — /api/product-integrations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.product_integrations.exceptions import (
    ProductBridgeDisabledError,
    ProductIntegrationAccessDeniedError,
    ProductIntegrationError,
    ProductIntegrationNotFoundError,
    ProductIntegrationValidationError,
)
from app.product_integrations.schemas import (
    BridgesOut,
    DeliveryListOut,
    DeliveryOut,
    PackageCreateIn,
    PackageListOut,
    PackageOut,
)
from app.product_integrations.service import ProductIntegrationService

router = APIRouter(
    prefix="/product-integrations",
    tags=["product-integrations"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> ProductIntegrationService:
    return ProductIntegrationService(db, audit_logger=AuditLogger(db))


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, ProductIntegrationNotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, ProductIntegrationAccessDeniedError):
        return HTTPException(status_code=403, detail=exc.message)
    if isinstance(exc, ProductBridgeDisabledError):
        return HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, ProductIntegrationValidationError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, ProductIntegrationError):
        return HTTPException(status_code=400, detail=exc.message)
    return HTTPException(status_code=400, detail="product_integration_error")


def _platform(auth: AuthContext) -> bool:
    perms = set(auth.permissions or [])
    return bool(perms & {"product_integrations.bridges.manage", "document_processing.jobs.manage", "*"})


@router.get("/bridges", response_model=BridgesOut)
def list_bridges(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.bridges.read")
    return BridgesOut(items=_svc(db).list_bridges_public())


@router.get("/packages", response_model=PackageListOut)
def list_packages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_id: str | None = Query(None),
    product_key: str | None = Query(None),
    status: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.packages.read")
    platform = _platform(auth)
    org_id = None if platform else auth.require_organization_id()
    items, total = _svc(db).list_packages(
        organization_id=org_id,
        product_key=product_key,
        document_id=document_id,
        status=status,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    return PackageListOut(
        items=[PackageOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/packages/{package_id}", response_model=PackageOut)
def get_package(
    package_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.packages.read")
    svc = _svc(db)
    try:
        row = (
            svc.get_package_platform(package_id)
            if _platform(auth)
            else svc.get_package_for_org(package_id, auth.require_organization_id())
        )
    except Exception as exc:
        raise _http(exc) from exc
    return PackageOut.model_validate(row)


@router.get("/deliveries", response_model=DeliveryListOut)
def list_deliveries(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    package_id: str | None = Query(None),
    product_key: str | None = Query(None),
    status: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.deliveries.read")
    platform = _platform(auth)
    org_id = None if platform else auth.require_organization_id()
    items, total = _svc(db).list_deliveries(
        organization_id=org_id,
        product_key=product_key,
        package_id=package_id,
        status=status,
        limit=limit,
        offset=offset,
        platform=platform,
    )
    return DeliveryListOut(
        items=[DeliveryOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/deliveries/{delivery_id}", response_model=DeliveryOut)
def get_delivery(
    delivery_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.deliveries.read")
    svc = _svc(db)
    try:
        row = (
            svc.get_delivery_platform(delivery_id)
            if _platform(auth)
            else svc.get_delivery_for_org(delivery_id, auth.require_organization_id())
        )
    except Exception as exc:
        raise _http(exc) from exc
    return DeliveryOut.model_validate(row)


@router.post("/comptapilot/packages", response_model=PackageOut, status_code=201)
def create_comptapilot_package(
    body: PackageCreateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.packages.create")
    auth.require("product_integrations.comptapilot.publish")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).create_comptapilot_package(
            organization_id=org_id,
            document_id=body.document_id,
            document_version_id=body.document_version_id,
            business_validation_id=body.business_validation_id,
            actor_user_id=auth.user.id if auth.user else None,
        )
    except Exception as exc:
        raise _http(exc) from exc
    return PackageOut.model_validate(row)


@router.post("/comptapilot/packages/{package_id}/deliver", response_model=DeliveryOut, status_code=201)
def deliver_comptapilot_package(
    package_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.deliveries.create")
    auth.require("product_integrations.comptapilot.publish")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).queue_delivery(
            package_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
        )
    except Exception as exc:
        raise _http(exc) from exc
    return DeliveryOut.model_validate(row)


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryOut)
def retry_delivery(
    delivery_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("product_integrations.deliveries.retry")
    platform = _platform(auth)
    org_id = 0 if platform else auth.require_organization_id()
    try:
        row = _svc(db).retry_delivery(
            delivery_id,
            org_id,
            actor_user_id=auth.user.id if auth.user else None,
            platform=platform,
        )
    except Exception as exc:
        raise _http(exc) from exc
    return DeliveryOut.model_validate(row)
