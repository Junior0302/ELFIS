"""Module central des abonnements ComptaPilot IA (org-scoped)."""

from app.subscriptions.access import get_subscription_access, serialize_access
from app.subscriptions.constants import PLAN_COMPTAPILOT_MONTHLY, PLANS
from app.subscriptions.permissions import can_access_feature, get_user_entitlements

__all__ = [
    "PLAN_COMPTAPILOT_MONTHLY",
    "PLANS",
    "can_access_feature",
    "get_subscription_access",
    "get_user_entitlements",
    "serialize_access",
]
