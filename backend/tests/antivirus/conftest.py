"""Fixtures antivirus — mock socket / verdicts. Pas de daemon ClamAV réel."""

from __future__ import annotations

import socket
from dataclasses import dataclass

import pytest

from app.security.antivirus import (
    AntivirusScanResult,
    AntivirusVerdict,
    ENGINE_CLAMD,
)

# Chaîne EICAR standard — fixture de test uniquement, jamais de malware réel.
EICAR_TEST = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


@dataclass
class FakeClamdSocket:
    response: bytes
    sent: bytearray
    closed: bool = False
    timeout: float | None = None
    fail_mode: str | None = None

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def sendall(self, data: bytes) -> None:
        if self.fail_mode == "timeout":
            raise socket.timeout("timed out")
        if self.fail_mode == "network":
            raise OSError("connection reset")
        self.sent.extend(data)

    def recv(self, n: int) -> bytes:
        if self.fail_mode == "timeout":
            raise socket.timeout("timed out")
        if self.fail_mode == "network":
            raise OSError("connection reset")
        chunk = self.response[:n]
        self.response = self.response[n:]
        return chunk

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def antivirus_clean(monkeypatch):
    """Fixture explicite : scanner clean (tests non liés à l'antivirus)."""

    result = AntivirusScanResult(
        verdict=AntivirusVerdict.CLEAN,
        engine=ENGINE_CLAMD,
        scanned=True,
        details={"reason": "ok", "fixture": "antivirus_clean"},
    )

    def _scan(**kwargs):
        return result

    monkeypatch.setattr("app.security.antivirus.scan_user_upload", _scan)
    monkeypatch.setattr("app.security.antivirus.require_clean_user_upload", _scan)
    return result


@pytest.fixture
def antivirus_enabled(monkeypatch):
    monkeypatch.setattr("app.config.settings.elfis_antivirus_enabled", True)
    monkeypatch.setattr("app.config.settings.elfis_antivirus_engine", "clamd")
    monkeypatch.setattr("app.config.settings.elfis_antivirus_fail_closed", True)
    monkeypatch.setattr("app.config.settings.clamd_host", "127.0.0.1")
    monkeypatch.setattr("app.config.settings.clamd_port", 3310)
    monkeypatch.setattr("app.config.settings.elfis_antivirus_timeout_seconds", 2.0)
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_enabled", True)
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_engine", "clamd")
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_fail_closed", True)
    monkeypatch.setattr("app.security.antivirus.settings.clamd_host", "127.0.0.1")
    monkeypatch.setattr("app.security.antivirus.settings.clamd_port", 3310)
    monkeypatch.setattr("app.security.antivirus.settings.elfis_antivirus_timeout_seconds", 2.0)


def install_fake_clamd(monkeypatch, *, response: bytes = b"stream: OK\n", fail_mode: str | None = None):
    state = {"socket": None}

    def _connect(address, timeout=None):
        sock = FakeClamdSocket(response=response, sent=bytearray(), fail_mode=fail_mode)
        state["socket"] = sock
        return sock

    monkeypatch.setattr("app.security.antivirus.socket.create_connection", _connect)
    return state
