"""SalesPilot Collaboration V1 — permissions."""

from __future__ import annotations

SALES_TEAM_READ = "sales.team.read"
SALES_TEAM_MANAGE = "sales.team.manage"
SALES_ASSIGN = "sales.assign"
SALES_REVIEW = "sales.review"
SALES_COMMENT = "sales.comment"
SALES_MENTION = "sales.mention"
SALES_TRANSFER = "sales.transfer"

SALES_COLLAB_PERMISSIONS: tuple[tuple[str, str], ...] = (
    (SALES_TEAM_READ, "sales"),
    (SALES_TEAM_MANAGE, "sales"),
    (SALES_ASSIGN, "sales"),
    (SALES_REVIEW, "sales"),
    (SALES_COMMENT, "sales"),
    (SALES_MENTION, "sales"),
    (SALES_TRANSFER, "sales"),
)

SALES_COLLAB_ROLE_GRANTS: dict[str, list[str]] = {
    "admin": [
        SALES_TEAM_READ,
        SALES_TEAM_MANAGE,
        SALES_ASSIGN,
        SALES_REVIEW,
        SALES_COMMENT,
        SALES_MENTION,
        SALES_TRANSFER,
    ],
    "cfo": [SALES_TEAM_READ, SALES_COMMENT],
    "comptable": [SALES_COMMENT],
    "employe": [
        SALES_TEAM_READ,
        SALES_ASSIGN,
        SALES_REVIEW,
        SALES_COMMENT,
        SALES_MENTION,
        SALES_TRANSFER,
    ],
    "auditeur": [SALES_TEAM_READ],
}
