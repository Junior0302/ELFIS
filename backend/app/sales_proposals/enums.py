"""Commercial Proposal Engine V1 — enums & workflow transitions."""

from __future__ import annotations

from enum import Enum


class ProposalType(str, Enum):
    quote = "quote"
    commercial_offer = "commercial_offer"
    service_proposal = "service_proposal"
    estimate = "estimate"
    renewal = "renewal"
    amendment = "amendment"
    subscription_offer = "subscription_offer"


class ProposalStatus(str, Enum):
    draft = "draft"
    preparing = "preparing"
    review_required = "review_required"
    approved = "approved"
    sent = "sent"
    viewed = "viewed"
    negotiating = "negotiating"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    converted = "converted"
    cancelled = "cancelled"


class VersionStatus(str, Enum):
    draft = "draft"
    preparing = "preparing"
    review_required = "review_required"
    approved = "approved"
    sent = "sent"
    viewed = "viewed"
    negotiating = "negotiating"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    converted = "converted"
    locked = "locked"
    cancelled = "cancelled"


class DiscountType(str, Enum):
    none = "none"
    percentage = "percentage"
    fixed = "fixed"


class AmountMode(str, Enum):
    calculated = "calculated"
    manual = "manual"
    hybrid_override = "hybrid_override"


class AmountOverrideReason(str, Enum):
    global_discount = "global_discount"
    package_price = "package_price"
    special_offer = "special_offer"
    negotiation = "negotiation"
    additional_service = "additional_service"
    rounding = "rounding"
    other = "other"


class ReadinessLevel(str, Enum):
    ready = "ready"
    almost_ready = "almost_ready"
    incomplete = "incomplete"
    blocked = "blocked"


class MatchLevel(str, Enum):
    exact_match = "exact_match"
    possible_match = "possible_match"
    no_match = "no_match"


# Proposal-level transitions
ALLOWED_TRANSITIONS: dict[ProposalStatus, frozenset[ProposalStatus]] = {
    ProposalStatus.draft: frozenset({ProposalStatus.preparing, ProposalStatus.cancelled}),
    ProposalStatus.preparing: frozenset(
        {ProposalStatus.review_required, ProposalStatus.approved, ProposalStatus.cancelled}
    ),
    ProposalStatus.review_required: frozenset(
        {ProposalStatus.preparing, ProposalStatus.approved, ProposalStatus.cancelled}
    ),
    ProposalStatus.approved: frozenset({ProposalStatus.sent, ProposalStatus.cancelled}),
    ProposalStatus.sent: frozenset(
        {
            ProposalStatus.viewed,
            ProposalStatus.negotiating,
            ProposalStatus.accepted,
            ProposalStatus.rejected,
            ProposalStatus.expired,
        }
    ),
    ProposalStatus.viewed: frozenset(
        {
            ProposalStatus.negotiating,
            ProposalStatus.accepted,
            ProposalStatus.rejected,
            ProposalStatus.expired,
        }
    ),
    ProposalStatus.negotiating: frozenset(
        {ProposalStatus.accepted, ProposalStatus.rejected, ProposalStatus.expired}
    ),
    ProposalStatus.accepted: frozenset({ProposalStatus.converted}),
    ProposalStatus.rejected: frozenset(),
    ProposalStatus.expired: frozenset(),
    ProposalStatus.converted: frozenset(),
    ProposalStatus.cancelled: frozenset(),
}

LOCKED_VERSION_STATUSES = frozenset(
    {
        VersionStatus.sent,
        VersionStatus.viewed,
        VersionStatus.negotiating,
        VersionStatus.accepted,
        VersionStatus.rejected,
        VersionStatus.expired,
        VersionStatus.converted,
        VersionStatus.locked,
    }
)

EDITABLE_VERSION_STATUSES = frozenset(
    {
        VersionStatus.draft,
        VersionStatus.preparing,
        VersionStatus.review_required,
        VersionStatus.approved,
    }
)
