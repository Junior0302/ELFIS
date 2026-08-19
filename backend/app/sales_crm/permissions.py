"""SalesPilot CRM Foundation V1 — permissions org RBAC."""

from __future__ import annotations

# Codes officiels S1.1 (exact match via AuthContext.require)
SALES_READ = "sales.read"
SALES_WRITE = "sales.write"
SALES_MANAGE = "sales.manage"
SALES_PIPELINE_MANAGE = "sales.pipeline.manage"
SALES_EXPORT = "sales.export"
SALES_ADMIN = "sales.admin"

SALES_PERMISSIONS: tuple[tuple[str, str], ...] = (
    (SALES_READ, "sales"),
    (SALES_WRITE, "sales"),
    (SALES_MANAGE, "sales"),
    (SALES_PIPELINE_MANAGE, "sales"),
    (SALES_EXPORT, "sales"),
    (SALES_ADMIN, "sales"),
)

# Rôles qui reçoivent les permissions sales (owner a déjà *)
SALES_ROLE_GRANTS: dict[str, list[str]] = {
    "admin": [
        SALES_READ,
        SALES_WRITE,
        SALES_MANAGE,
        SALES_PIPELINE_MANAGE,
        SALES_EXPORT,
        SALES_ADMIN,
    ],
    "cfo": [SALES_READ, SALES_EXPORT],
    "comptable": [SALES_READ],
    "employe": [SALES_READ, SALES_WRITE],
    "auditeur": [SALES_READ],
}
