"""Antivirus production ELFIS — client clamd INSTREAM + politique fail-closed.

Ne jamais logger le contenu d'un fichier, un nom complet, une clé ou des données métier.
"""

from __future__ import annotations

import logging
import socket
import struct
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Iterator

from app.config import settings
from app.observability.metrics import metrics_registry
from app.security.security_config import environment_name, is_production

logger = logging.getLogger(__name__)

INSTREAM_CHUNK_SIZE = 65_536
CLAMD_INSTREAM_CMD = b"zINSTREAM\x00"

USER_UPLOAD_SOURCES = frozenset(
    {"upload", "email_attachment", "import", "api", "user_upload"}
)
GENERATED_BY_ELFIS_SOURCES = frozenset({"generated", "system", "generated_by_elfis"})

CONTENT_ORIGIN_USER_UPLOAD = "user_upload"
CONTENT_ORIGIN_GENERATED = "generated_by_elfis"
CONTENT_ORIGIN_UNKNOWN = "unknown"
LEGACY_UNCLASSIFIED_ORIGINS = frozenset({"", CONTENT_ORIGIN_UNKNOWN})

SCAN_STATUS_CLEAN = "clean"
SCAN_STATUS_INFECTED = "infected"
SCAN_STATUS_UNAVAILABLE = "unavailable"
SCAN_STATUS_UNKNOWN = "unknown"
SCAN_STATUS_PENDING = "pending"

ENGINE_CLAMD = "clamd"
ENGINE_DISABLED = "disabled"
ENGINE_ELFIS_GENERATED = "elfis_generated"


class AntivirusVerdict(str, Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class AntivirusErrorCode:
    FILE_INFECTED = "file_infected"
    ANTIVIRUS_UNAVAILABLE = "antivirus_unavailable"
    FILE_SCAN_FAILED = "file_scan_failed"
    FILE_SCAN_REQUIRED = "file_scan_required"


_HTTP_STATUS = {
    AntivirusErrorCode.FILE_INFECTED: 422,
    AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE: 503,
    AntivirusErrorCode.FILE_SCAN_FAILED: 422,
    AntivirusErrorCode.FILE_SCAN_REQUIRED: 409,
}

_USER_MESSAGES = {
    AntivirusErrorCode.FILE_INFECTED: "Fichier refusé : contenu malveillant détecté",
    AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE: "Scan antivirus indisponible",
    AntivirusErrorCode.FILE_SCAN_FAILED: "Échec du scan antivirus",
    AntivirusErrorCode.FILE_SCAN_REQUIRED: "Téléchargement refusé : scan antivirus requis",
}


@dataclass(frozen=True)
class AntivirusScanResult:
    verdict: AntivirusVerdict
    engine: str
    signature: str | None = None
    scanned: bool = False
    details: dict = field(default_factory=dict)

    @property
    def persist_status(self) -> str:
        if self.verdict == AntivirusVerdict.CLEAN:
            return SCAN_STATUS_CLEAN
        if self.verdict == AntivirusVerdict.INFECTED:
            return SCAN_STATUS_INFECTED
        if self.verdict == AntivirusVerdict.UNAVAILABLE:
            return SCAN_STATUS_UNAVAILABLE
        return SCAN_STATUS_UNKNOWN

    @property
    def is_clean(self) -> bool:
        return self.verdict == AntivirusVerdict.CLEAN


class AntivirusError(Exception):
    def __init__(
        self,
        code: str,
        message: str = "",
        *,
        http_status: int | None = None,
        result: AntivirusScanResult | None = None,
    ) -> None:
        self.code = code
        self.message = message or _USER_MESSAGES.get(code, "Scan antivirus refusé")
        self.http_status = http_status or _HTTP_STATUS.get(code, 422)
        self.result = result
        super().__init__(self.message)


def antivirus_max_bytes() -> int:
    configured = int(getattr(settings, "elfis_antivirus_max_bytes", 0) or 0)
    if configured > 0:
        return configured
    return int(getattr(settings, "storage_max_file_size_bytes", 15 * 1024 * 1024) or 15 * 1024 * 1024)


def antivirus_enabled() -> bool:
    return bool(getattr(settings, "elfis_antivirus_enabled", False))


def antivirus_fail_closed() -> bool:
    return bool(getattr(settings, "elfis_antivirus_fail_closed", True))


def antivirus_engine_name() -> str:
    return (getattr(settings, "elfis_antivirus_engine", None) or ENGINE_CLAMD).strip().lower() or ENGINE_CLAMD


def allows_explicit_scanner_disable() -> bool:
    """Désactivation explicite autorisée uniquement hors production (dev/test)."""
    return environment_name() in {"development", "test"}


def normalize_content_origin(content_origin: str | None, source: str | None = None) -> str:
    raw = (content_origin or source or "").strip().lower()
    return raw or CONTENT_ORIGIN_UNKNOWN


def is_user_upload_source(source: str | None) -> bool:
    raw = normalize_content_origin(source)
    if raw in GENERATED_BY_ELFIS_SOURCES or raw in LEGACY_UNCLASSIFIED_ORIGINS:
        return False
    return raw in USER_UPLOAD_SOURCES or raw not in GENERATED_BY_ELFIS_SOURCES


def persist_scan_fields(result: AntivirusScanResult) -> dict:
    from datetime import datetime

    return {
        "scan_status": result.persist_status,
        "scan_engine": (result.engine or "")[:64] or None,
        "scan_signature": (result.signature or None),
        "scan_at": datetime.utcnow() if result.scanned or result.verdict != AntivirusVerdict.CLEAN else datetime.utcnow(),
    }


def _record_metrics(*, result: AntivirusScanResult, upload_type: str) -> None:
    labels = {
        "engine": (result.engine or "unknown")[:32],
        "result": result.verdict.value,
        "upload_type": (upload_type or "unknown")[:32],
    }
    try:
        metrics_registry.incr("antivirus_scan_total", labels=labels)
        if result.verdict == AntivirusVerdict.CLEAN:
            metrics_registry.incr("antivirus_scan_clean_total", labels=labels)
        elif result.verdict == AntivirusVerdict.INFECTED:
            metrics_registry.incr("antivirus_scan_infected_total", labels=labels)
        else:
            metrics_registry.incr("antivirus_scan_failed_total", labels=labels)
    except Exception:
        logger.debug("antivirus_metrics_failed", exc_info=True)


def _log_scan(*, result: AntivirusScanResult, upload_type: str) -> None:
    logger.info(
        "antivirus_scan",
        extra={
            "engine": result.engine,
            "result": result.verdict.value,
            "upload_type": upload_type,
            "scanned": result.scanned,
            "has_signature": bool(result.signature),
        },
    )


def _disabled_skip_result() -> AntivirusScanResult:
    return AntivirusScanResult(
        verdict=AntivirusVerdict.CLEAN,
        engine=ENGINE_DISABLED,
        signature=None,
        scanned=False,
        details={"reason": "scanner_disabled_non_production"},
    )


def _unavailable_result(*, reason: str, engine: str | None = None) -> AntivirusScanResult:
    return AntivirusScanResult(
        verdict=AntivirusVerdict.UNAVAILABLE,
        engine=engine or antivirus_engine_name(),
        signature=None,
        scanned=False,
        details={"reason": reason},
    )


def _error_result(*, reason: str, engine: str | None = None) -> AntivirusScanResult:
    return AntivirusScanResult(
        verdict=AntivirusVerdict.ERROR,
        engine=engine or antivirus_engine_name(),
        signature=None,
        scanned=False,
        details={"reason": reason},
    )


def error_from_result(result: AntivirusScanResult) -> AntivirusError:
    if result.verdict == AntivirusVerdict.INFECTED:
        return AntivirusError(AntivirusErrorCode.FILE_INFECTED, result=result)
    if result.verdict == AntivirusVerdict.UNAVAILABLE:
        return AntivirusError(AntivirusErrorCode.ANTIVIRUS_UNAVAILABLE, result=result)
    return AntivirusError(AntivirusErrorCode.FILE_SCAN_FAILED, result=result)


def require_clean_result(result: AntivirusScanResult) -> AntivirusScanResult:
    if result.is_clean:
        return result
    raise error_from_result(result)


def assert_scan_allows_download(
    *,
    scan_status: str | None,
    source: str | None = None,
    content_origin: str | None = None,
) -> None:
    """Garde download — politique provenance explicite.

    - infected : toujours refusé
    - generated_by_elfis / generated / system : autorisé si non infected
    - user_upload / unknown / absent : uniquement si scan_status=clean
    - unknown n'est jamais traité comme generated_by_elfis
    """
    origin = normalize_content_origin(content_origin, source)
    status = (scan_status or SCAN_STATUS_UNKNOWN).strip().lower() or SCAN_STATUS_UNKNOWN

    if status == SCAN_STATUS_INFECTED:
        raise AntivirusError(AntivirusErrorCode.FILE_INFECTED)

    if origin in GENERATED_BY_ELFIS_SOURCES:
        return

    if status == SCAN_STATUS_CLEAN:
        return

    raise AntivirusError(AntivirusErrorCode.FILE_SCAN_REQUIRED)


def parse_clamd_response(raw: bytes | str) -> AntivirusScanResult:
    engine = ENGINE_CLAMD
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    text = text.rstrip("\x00\r\n")
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    line = line.rstrip("\x00\r\n")
    if not line:
        return _error_result(reason="empty_response", engine=engine)
    lowered = line.lower()
    if lowered.endswith(" ok") or lowered == "ok" or lowered.endswith(": ok"):
        return AntivirusScanResult(
            verdict=AntivirusVerdict.CLEAN,
            engine=engine,
            scanned=True,
            details={"reason": "ok"},
        )
    if "found" in lowered:
        signature = _extract_signature(line)
        return AntivirusScanResult(
            verdict=AntivirusVerdict.INFECTED,
            engine=engine,
            signature=signature,
            scanned=True,
            details={"reason": "found"},
        )
    if "error" in lowered:
        return _error_result(reason="clamd_error", engine=engine)
    return _error_result(reason="malformed_response", engine=engine)


def _extract_signature(line: str) -> str | None:
    # "stream: Eicar-Test-File FOUND" — jamais de chemin / contenu
    body = line
    if ":" in body:
        body = body.split(":", 1)[1].strip()
    if body.lower().endswith("found"):
        body = body[: -len("found")].strip()
    cleaned = "".join(ch for ch in body if ch.isprintable())[:128]
    return cleaned or None


class ClamdInstreamClient:
    """Client TCP clamd — commande INSTREAM, fichier complet, stdlib socket."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        max_bytes: int,
        chunk_size: int = INSTREAM_CHUNK_SIZE,
    ) -> None:
        self.host = (host or "").strip()
        self.port = int(port or 3310)
        self.timeout_seconds = float(timeout_seconds or 20)
        self.max_bytes = int(max_bytes)
        self.chunk_size = max(1024, int(chunk_size or INSTREAM_CHUNK_SIZE))

    def scan_bytes(self, data: bytes) -> AntivirusScanResult:
        return self.scan_chunks(_iter_bytes(data, self.chunk_size), size_hint=len(data))

    def scan_path(self, path: str | Path) -> AntivirusScanResult:
        file_path = Path(path)
        size = file_path.stat().st_size
        with file_path.open("rb") as fh:
            return self.scan_stream(fh, size_hint=size)

    def scan_stream(self, stream: BinaryIO, *, size_hint: int | None = None) -> AntivirusScanResult:
        return self.scan_chunks(_iter_stream(stream, self.chunk_size), size_hint=size_hint)

    def scan_chunks(
        self,
        chunks: Iterator[bytes],
        *,
        size_hint: int | None = None,
    ) -> AntivirusScanResult:
        if not self.host:
            return _unavailable_result(reason="clamd_host_missing")
        if size_hint is not None and size_hint > self.max_bytes:
            return _error_result(reason="max_bytes_exceeded")

        sock: socket.socket | None = None
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout_seconds)
            sock.settimeout(self.timeout_seconds)
            sock.sendall(CLAMD_INSTREAM_CMD)
            sent = 0
            for chunk in chunks:
                if not chunk:
                    continue
                sent += len(chunk)
                if sent > self.max_bytes:
                    return _error_result(reason="max_bytes_exceeded")
                sock.sendall(struct.pack(">I", len(chunk)))
                sock.sendall(chunk)
            sock.sendall(struct.pack(">I", 0))
            raw = _recv_response(sock)
            return parse_clamd_response(raw)
        except TimeoutError:
            return _unavailable_result(reason="timeout")
        except socket.timeout:
            return _unavailable_result(reason="timeout")
        except OSError:
            return _unavailable_result(reason="network_error")
        except Exception:
            return _error_result(reason="scan_exception")
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass


def _iter_bytes(data: bytes, chunk_size: int) -> Iterator[bytes]:
    view = memoryview(data)
    for offset in range(0, len(data), chunk_size):
        yield bytes(view[offset : offset + chunk_size])


def _iter_stream(stream: BinaryIO, chunk_size: int) -> Iterator[bytes]:
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        yield chunk


def _recv_response(sock: socket.socket) -> bytes:
    buf = bytearray()
    while True:
        piece = sock.recv(4096)
        if not piece:
            break
        buf.extend(piece)
        if b"\n" in piece or b"\x00" in piece:
            break
        if len(buf) > 4096:
            break
    return bytes(buf)


def _build_client() -> ClamdInstreamClient:
    return ClamdInstreamClient(
        host=str(getattr(settings, "clamd_host", "") or ""),
        port=int(getattr(settings, "clamd_port", 3310) or 3310),
        timeout_seconds=float(getattr(settings, "elfis_antivirus_timeout_seconds", 20) or 20),
        max_bytes=antivirus_max_bytes(),
        chunk_size=int(getattr(settings, "storage_upload_chunk_size_bytes", INSTREAM_CHUNK_SIZE) or INSTREAM_CHUNK_SIZE),
    )


def scan_user_upload(
    *,
    data: bytes | None = None,
    path: str | Path | None = None,
    stream: BinaryIO | None = None,
    upload_type: str,
    size_hint: int | None = None,
) -> AntivirusScanResult:
    """Scan un upload utilisateur. Fail-closed en production. Jamais de bypass implicite."""
    engine = antivirus_engine_name()

    if not antivirus_enabled():
        if is_production() or not allows_explicit_scanner_disable():
            result = _unavailable_result(reason="scanner_disabled_production", engine=engine)
            _record_metrics(result=result, upload_type=upload_type)
            _log_scan(result=result, upload_type=upload_type)
            return result
        result = _disabled_skip_result()
        _record_metrics(result=result, upload_type=upload_type)
        _log_scan(result=result, upload_type=upload_type)
        return result

    if engine != ENGINE_CLAMD:
        result = _unavailable_result(reason="engine_unsupported", engine=engine)
        _record_metrics(result=result, upload_type=upload_type)
        _log_scan(result=result, upload_type=upload_type)
        return result

    client = _build_client()
    if data is not None:
        result = client.scan_bytes(data)
    elif path is not None:
        result = client.scan_path(path)
    elif stream is not None:
        result = client.scan_stream(stream, size_hint=size_hint)
    else:
        result = _error_result(reason="no_input")

    _record_metrics(result=result, upload_type=upload_type)
    _log_scan(result=result, upload_type=upload_type)
    return result


def require_clean_user_upload(
    *,
    data: bytes | None = None,
    path: str | Path | None = None,
    stream: BinaryIO | None = None,
    upload_type: str,
    size_hint: int | None = None,
) -> AntivirusScanResult:
    """Scan puis refuse tout verdict autre que clean (fail-closed)."""
    result = scan_user_upload(
        data=data,
        path=path,
        stream=stream,
        upload_type=upload_type,
        size_hint=size_hint,
    )
    return require_clean_result(result)


def http_detail(exc: AntivirusError) -> dict[str, str]:
    return {"code": exc.code, "message": exc.message}
