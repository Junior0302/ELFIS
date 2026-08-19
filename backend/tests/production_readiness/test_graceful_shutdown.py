"""Arrêt gracieux — hooks reliability."""

from __future__ import annotations

from app.reliability.shutdown_service import (
    is_accepting_jobs,
    register_shutdown_hook,
    run_shutdown,
    stop_accepting_jobs,
)


def test_graceful_shutdown_runs_hooks():
    from app.reliability import shutdown_service as ss

    ss._hooks.clear()  # noqa: SLF001
    ss._accepting_jobs = True  # noqa: SLF001
    called: list[str] = []

    def _hook() -> None:
        called.append("ok")

    register_shutdown_hook(_hook)
    run_shutdown()
    assert called == ["ok"]
    assert is_accepting_jobs() is False


def test_graceful_stop_accepting_idempotent():
    from app.reliability import shutdown_service as ss

    ss._accepting_jobs = True  # noqa: SLF001
    stop_accepting_jobs()
    stop_accepting_jobs()
    assert is_accepting_jobs() is False
