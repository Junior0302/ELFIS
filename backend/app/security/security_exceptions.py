"""Exceptions et format d'erreur normalisé."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from app.security.security_redaction import filter_error_details, safe_exception_message
from app.security.security_types import ErrorCode


class SecurityError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def build_error_body(
    *,
    code: str,
    message: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
    details: dict[str, Any] | None = None,
    legacy_detail: Any = None,
) -> dict[str, Any]:
    """Format normalisé + compatibilité historique `detail`."""
    error = {
        "code": code,
        "message": message,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "details": filter_error_details(details),
    }
    body: dict[str, Any] = {"error": error}
    if legacy_detail is not None:
        body["detail"] = legacy_detail
    else:
        # Compat frontend / clients existants
        body["detail"] = {"code": code, "message": message, **(details or {})}
    return body


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    legacy_detail: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_body(
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
            details=details,
            legacy_detail=legacy_detail,
        ),
        headers=headers or {},
    )


def http_exception_to_body(
    exc: Any,
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    detail = getattr(exc, "detail", "Erreur")
    status_code = int(getattr(exc, "status_code", 500))
    code = ErrorCode.INTERNAL_ERROR
    message = "Erreur"
    details: dict[str, Any] = {}

    if isinstance(detail, dict):
        code = str(detail.get("code") or code)
        message = str(detail.get("message") or detail.get("msg") or message)
        details = {k: v for k, v in detail.items() if k not in {"code", "message", "msg"}}
    elif isinstance(detail, str):
        message = detail
        lowered = detail.lower()
        if "authentif" in lowered or "token" in lowered:
            code = ErrorCode.AUTHENTICATION_REQUIRED if "authentif" in lowered else ErrorCode.INVALID_TOKEN
        elif "permission" in lowered:
            code = ErrorCode.PERMISSION_DENIED
        else:
            code = ErrorCode.VALIDATION_ERROR if status_code == 422 else (
                ErrorCode.AUTHENTICATION_REQUIRED if status_code == 401 else (
                    ErrorCode.PERMISSION_DENIED if status_code == 403 else (
                        ErrorCode.RESOURCE_NOT_FOUND if status_code == 404 else (
                            ErrorCode.PAYLOAD_TOO_LARGE if status_code == 413 else (
                                ErrorCode.RATE_LIMIT_EXCEEDED if status_code == 429 else code
                            )
                        )
                    )
                )
            )
    else:
        message = safe_exception_message(detail)

    if status_code == 401 and code == ErrorCode.INTERNAL_ERROR:
        code = ErrorCode.AUTHENTICATION_REQUIRED
    elif status_code == 403 and code == ErrorCode.INTERNAL_ERROR:
        code = ErrorCode.PERMISSION_DENIED
    elif status_code == 404:
        code = ErrorCode.RESOURCE_NOT_FOUND
    elif status_code == 413:
        code = ErrorCode.PAYLOAD_TOO_LARGE
    elif status_code == 429:
        code = ErrorCode.RATE_LIMIT_EXCEEDED
    elif status_code == 422:
        code = ErrorCode.VALIDATION_ERROR

    return build_error_body(
        code=code,
        message=message,
        request_id=request_id,
        correlation_id=correlation_id,
        details=details,
        legacy_detail=detail,
    )
