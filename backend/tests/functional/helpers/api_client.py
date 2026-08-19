"""Helpers API de recette fonctionnelle."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.services.auth import create_access_token
from tests.functional.catalog import TEST_PASSWORD, USERS


class FunctionalApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None, request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.request_id = request_id


class FunctionalClient:
    def __init__(self, client: TestClient, *, seed: dict[str, Any]):
        self.client = client
        self.seed = seed
        self.token: str | None = None
        self.org_id: int | None = None
        self.user_key: str | None = None

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        h: dict[str, str] = {"X-Request-Id": f"func-{int(time.time() * 1000)}"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if self.org_id is not None:
            h["X-Organization-Id"] = str(self.org_id)
        if extra:
            h.update(extra)
        return h

    def _check(self, response, *, expect: int | tuple[int, ...] | None = None) -> Any:
        expect_set = None
        if expect is None:
            pass
        elif isinstance(expect, int):
            expect_set = {expect}
        else:
            expect_set = set(expect)
        rid = response.headers.get("X-Request-Id")
        if expect_set is not None and response.status_code not in expect_set:
            raise FunctionalApiError(
                f"HTTP {response.status_code} (attendu {expect_set}) body={response.text[:500]}",
                status_code=response.status_code,
                body=_safe_json(response),
                request_id=rid,
            )
        return _safe_json(response)

    def login_user(self, user_key: str) -> dict[str, Any]:
        """Émet un JWT de recette (POST /login désactivé — Firebase en UI)."""
        info = self.seed["users"][user_key]
        token = create_access_token({"sub": str(info["id"]), "org_id": info.get("org_id")})
        self.token = token
        self.org_id = info.get("org_id")
        self.user_key = user_key
        return {"token": token, "user": info, "password_unused_for_api": TEST_PASSWORD}

    def select_organization(self, org_key: str) -> int:
        org = self.seed["organizations"][org_key]
        self.org_id = org["id"]
        return self.org_id

    def get_me(self) -> dict[str, Any]:
        r = self.client.get("/api/auth/me", headers=self._headers())
        return self._check(r, expect=200)

    def upload_document(
        self,
        file_path: Path | bytes,
        *,
        filename: str = "invoice.pdf",
        document_type: str = "supplier_invoice",
        content_type: str = "application/pdf",
        expect: int | tuple[int, ...] = 200,
    ) -> dict[str, Any]:
        if isinstance(file_path, Path):
            content = file_path.read_bytes()
            filename = file_path.name
        else:
            content = file_path
        files = {"file": (filename, content, content_type)}
        data = {
            "tenant_id": str(self.org_id or ""),
            "document_type": document_type,
        }
        r = self.client.post(
            "/api/vault/documents/archive",
            headers=self._headers(),
            files=files,
            data=data,
        )
        return self._check(r, expect=expect)

    def list_documents(self) -> dict[str, Any]:
        r = self.client.get("/api/vault/documents", headers=self._headers())
        return self._check(r, expect=200)

    def search_resources(self, q: str) -> dict[str, Any]:
        r = self.client.get(f"/api/search?q={q}", headers=self._headers())
        return self._check(r, expect=(200, 404, 402, 403))

    def get_notifications(self) -> dict[str, Any]:
        r = self.client.get("/api/notifications", headers=self._headers())
        return self._check(r, expect=(200, 401, 403))

    def get_subscription(self) -> dict[str, Any]:
        r = self.client.get("/api/subscriptions/status", headers=self._headers())
        if r.status_code == 404:
            r = self.client.get("/api/billing/subscription", headers=self._headers())
        return self._check(r, expect=(200, 402, 403, 404))

    def get_admin_dashboard(self) -> dict[str, Any]:
        r = self.client.get("/api/platform/dashboard", headers=self._headers())
        return self._check(r, expect=200)

    def get_health_live(self) -> dict[str, Any]:
        r = self.client.get("/api/health/live")
        return self._check(r, expect=200)

    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout_s: float = 8.0,
        interval_s: float = 0.2,
        process_fn=None,
    ) -> dict[str, Any]:
        """Polling borné — optionnellement process_fn() pour avancer le worker sync."""
        deadline = time.monotonic() + timeout_s
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            if process_fn:
                process_fn()
            r = self.client.get(f"/api/jobs/{job_id}", headers=self._headers())
            if r.status_code == 200:
                last = r.json()
                status = (last.get("status") or last.get("job", {}).get("status") or "").lower()
                if status in {"completed", "failed", "dead_letter", "cancelled"}:
                    return last
            time.sleep(interval_s)
        raise FunctionalApiError(
            f"Timeout wait_for_job({job_id})",
            body=last,
        )


def _safe_json(response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:1000]}


def user_email(key: str) -> str:
    return USERS[key].email
