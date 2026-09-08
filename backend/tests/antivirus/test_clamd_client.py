"""Client clamd INSTREAM — socket mocké, pas de daemon réel."""

from __future__ import annotations

import struct

from app.security.antivirus import (
    CLAMD_INSTREAM_CMD,
    ClamdInstreamClient,
    parse_clamd_response,
    AntivirusVerdict,
)
from tests.antivirus.conftest import EICAR_TEST, install_fake_clamd


def test_parse_ok():
    result = parse_clamd_response(b"stream: OK\n")
    assert result.verdict == AntivirusVerdict.CLEAN
    assert result.scanned is True
    assert result.engine == "clamd"


def test_parse_eicar_found():
    result = parse_clamd_response(b"stream: Eicar-Test-File FOUND\n")
    assert result.verdict == AntivirusVerdict.INFECTED
    assert result.signature == "Eicar-Test-File"
    assert result.scanned is True


def test_parse_error():
    result = parse_clamd_response(b"INSTREAM size limit exceeded. ERROR\n")
    assert result.verdict == AntivirusVerdict.ERROR


def test_parse_malformed():
    result = parse_clamd_response(b"??? unexpected\n")
    assert result.verdict == AntivirusVerdict.ERROR
    assert result.details.get("reason") == "malformed_response"


def test_parse_empty():
    result = parse_clamd_response(b"")
    assert result.verdict == AntivirusVerdict.ERROR


def test_instream_sends_full_file_and_zero_chunk(monkeypatch):
    state = install_fake_clamd(monkeypatch, response=b"stream: OK\n")
    client = ClamdInstreamClient(
        host="127.0.0.1", port=3310, timeout_seconds=2, max_bytes=1024, chunk_size=8
    )
    payload = b"%PDF-1.4 " + (b"A" * 40)
    result = client.scan_bytes(payload)
    assert result.verdict == AntivirusVerdict.CLEAN
    sent = bytes(state["socket"].sent)
    assert sent.startswith(CLAMD_INSTREAM_CMD)
    assert sent.endswith(struct.pack(">I", 0))
    assert payload in sent
    assert state["socket"].closed is True


def test_eicar_fixture_infected(monkeypatch):
    install_fake_clamd(monkeypatch, response=b"stream: Eicar-Test-File FOUND\n")
    client = ClamdInstreamClient(
        host="127.0.0.1", port=3310, timeout_seconds=2, max_bytes=1024
    )
    result = client.scan_bytes(EICAR_TEST)
    assert result.verdict == AntivirusVerdict.INFECTED
    assert result.signature == "Eicar-Test-File"


def test_timeout_unavailable(monkeypatch):
    install_fake_clamd(monkeypatch, fail_mode="timeout")
    client = ClamdInstreamClient(
        host="127.0.0.1", port=3310, timeout_seconds=1, max_bytes=1024
    )
    result = client.scan_bytes(b"%PDF-1.4 clean")
    assert result.verdict == AntivirusVerdict.UNAVAILABLE
    assert result.details.get("reason") == "timeout"


def test_network_error_unavailable(monkeypatch):
    install_fake_clamd(monkeypatch, fail_mode="network")
    client = ClamdInstreamClient(
        host="127.0.0.1", port=3310, timeout_seconds=1, max_bytes=1024
    )
    result = client.scan_bytes(b"%PDF-1.4 clean")
    assert result.verdict == AntivirusVerdict.UNAVAILABLE


def test_missing_host_unavailable():
    client = ClamdInstreamClient(host="", port=3310, timeout_seconds=1, max_bytes=1024)
    result = client.scan_bytes(b"%PDF-1.4")
    assert result.verdict == AntivirusVerdict.UNAVAILABLE
    assert result.details.get("reason") == "clamd_host_missing"
