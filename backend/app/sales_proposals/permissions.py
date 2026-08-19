"""SalesPilot proposal permissions."""

from __future__ import annotations

PROPOSALS_READ = "sales.proposals.read"
PROPOSALS_WRITE = "sales.proposals.write"
PROPOSALS_APPROVE = "sales.proposals.approve"
PROPOSALS_SEND = "sales.proposals.send"
PROPOSALS_ACCEPT = "sales.proposals.accept"
PROPOSALS_CONVERT = "sales.proposals.convert"
PROPOSALS_DELETE = "sales.proposals.delete"
PROPOSALS_ADMIN = "sales.proposals.admin"

PROPOSAL_PERMISSIONS: tuple[tuple[str, str], ...] = (
    (PROPOSALS_READ, "sales"),
    (PROPOSALS_WRITE, "sales"),
    (PROPOSALS_APPROVE, "sales"),
    (PROPOSALS_SEND, "sales"),
    (PROPOSALS_ACCEPT, "sales"),
    (PROPOSALS_CONVERT, "sales"),
    (PROPOSALS_DELETE, "sales"),
    (PROPOSALS_ADMIN, "sales"),
)

# Backward-compatible aliases used by AuthContext.require when role has sales.write
PROPOSAL_ROLE_GRANTS: dict[str, list[str]] = {
    "admin": [
        PROPOSALS_READ,
        PROPOSALS_WRITE,
        PROPOSALS_APPROVE,
        PROPOSALS_SEND,
        PROPOSALS_ACCEPT,
        PROPOSALS_CONVERT,
        PROPOSALS_DELETE,
        PROPOSALS_ADMIN,
    ],
    "cfo": [PROPOSALS_READ],
    "comptable": [PROPOSALS_READ],
    "employe": [
        PROPOSALS_READ,
        PROPOSALS_WRITE,
        PROPOSALS_SEND,
        PROPOSALS_ACCEPT,
    ],
    "auditeur": [PROPOSALS_READ],
}
