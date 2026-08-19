"""Sales Intelligence permissions."""

from __future__ import annotations

INTEL_READ = "sales.intelligence.read"
INTEL_MANAGE = "sales.intelligence.manage"
INTEL_DISMISS = "sales.intelligence.dismiss"
INTEL_SYNC = "sales.intelligence.sync"

INTEL_PERMISSIONS: tuple[tuple[str, str], ...] = (
    (INTEL_READ, "sales"),
    (INTEL_MANAGE, "sales"),
    (INTEL_DISMISS, "sales"),
    (INTEL_SYNC, "sales"),
)

INTEL_ROLE_GRANTS: dict[str, list[str]] = {
    "admin": [INTEL_READ, INTEL_MANAGE, INTEL_DISMISS, INTEL_SYNC],
    "cfo": [INTEL_READ],
    "comptable": [INTEL_READ],
    "employe": [INTEL_READ, INTEL_DISMISS],
    "auditeur": [INTEL_READ],
}
