"""Available actions for insights — routes come from backend only."""

from __future__ import annotations

from typing import Any


def action(
    *,
    action_type: str,
    label: str,
    route: str | None = None,
    enabled: bool = True,
    disabled_reason: str | None = None,
    required_permission: str | None = "sales.read",
    requires_confirmation: bool = False,
    expected_resolution_behavior: str | None = None,
) -> dict[str, Any]:
    return {
        "action_type": action_type,
        "label": label,
        "route": route,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "required_permission": required_permission,
        "requires_confirmation": requires_confirmation,
        "expected_resolution_behavior": expected_resolution_behavior,
    }


def standard_actions(
    *,
    primary: dict[str, Any],
    can_dismiss: bool = True,
) -> list[dict[str, Any]]:
    items = [primary]
    items.append(
        action(
            action_type="acknowledge",
            label="Marquer comme vu",
            enabled=True,
            required_permission="sales.intelligence.read",
            expected_resolution_behavior="acknowledge_only",
        )
    )
    if can_dismiss:
        items.append(
            action(
                action_type="dismiss",
                label="Écarter",
                enabled=True,
                required_permission="sales.intelligence.dismiss",
                requires_confirmation=True,
                expected_resolution_behavior="dismiss_until_changed",
            )
        )
    return items
