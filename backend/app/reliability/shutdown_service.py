"""Arrêt propre — hooks shutdown."""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("elfis.reliability.shutdown")

_hooks: list[Callable[[], None]] = []
_accepting_jobs = True


def register_shutdown_hook(fn: Callable[[], None]) -> None:
    _hooks.append(fn)


def stop_accepting_jobs() -> None:
    global _accepting_jobs
    _accepting_jobs = False


def is_accepting_jobs() -> bool:
    return _accepting_jobs


def run_shutdown() -> None:
    stop_accepting_jobs()
    for hook in list(_hooks):
        try:
            hook()
        except Exception:
            logger.exception("shutdown_hook_failed")
    logger.info("shutdown_completed")
