"""Tests routes /api/admin/system/* — IAM permissions."""

from __future__ import annotations

import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.iam.permission_catalog import all_permissions
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context
from app.routers import admin_system_health
from app.system_health.health_registry import reset_default_registry_for_tests


class AdminSystemHealthRoutesTests(unittest.TestCase):
    def setUp(self):
        reset_default_registry_for_tests()
        app = FastAPI()
        app.include_router(admin_system_health.router, prefix="/api")

        def _admin_ctx():
            return PermissionContext(
                user_id=10,
                is_authenticated=True,
                is_platform_admin=True,
                platform_role="platform_admin",
                permissions=frozenset(
                    {
                        "system.health.read",
                        "system.metrics.read",
                        "system.alerts.read",
                        "system.logs.read",
                    }
                ),
            )

        app.dependency_overrides[get_permission_context] = _admin_ctx
        self.client = TestClient(app)
        self.app = app

    def tearDown(self):
        reset_default_registry_for_tests()

    def test_health_200_schema(self):
        res = self.client.get("/api/admin/system/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("overall_status", body)
        self.assertIn("services", body)
        self.assertIsInstance(body["services"], list)
        self.assertGreaterEqual(len(body["services"]), 12)
        blob = res.text.lower()
        for forbidden in ("sk_live", "service_role", "password=", "whsec_"):
            self.assertNotIn(forbidden, blob)
        # Ne pas exposer le catalogue permissions
        self.assertNotIn("system.health.refresh", blob)

    def test_metrics_period(self):
        res = self.client.get("/api/admin/system/metrics?period=24h")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["period"], "24h")
        self.assertIn("metrics", body)

    def test_alerts(self):
        res = self.client.get("/api/admin/system/alerts")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("alerts", body)
        self.assertGreaterEqual(body["active_count"], 1)

    def test_logs_filters(self):
        res = self.client.get("/api/admin/system/logs?limit=50&level=error")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(all(e["level"] == "error" for e in body["entries"]))

    def test_permission_required(self):
        def _deny():
            raise HTTPException(403, detail={"code": "permission_denied", "message": "Accès refusé"})

        # Simule un contexte authentifié sans permission
        def _no_perm():
            return PermissionContext(
                user_id=2,
                is_authenticated=True,
                permissions=frozenset(),
            )

        self.app.dependency_overrides[get_permission_context] = _no_perm
        res = self.client.get("/api/admin/system/health")
        self.assertEqual(res.status_code, 403)
        detail = res.json().get("detail") or {}
        self.assertEqual(detail.get("code"), "permission_denied")
        # Pas de liste complète des permissions
        self.assertNotIn("permissions", detail)
        blob = res.text
        for p in list(all_permissions())[:5]:
            if p not in {"system.health.read"}:  # may appear in message? shouldn't
                pass
        self.assertNotIn("vault.secrets.manage", blob)

    def test_unauthenticated_401(self):
        def _anon():
            return PermissionContext(is_authenticated=False)

        self.app.dependency_overrides[get_permission_context] = _anon
        res = self.client.get("/api/admin/system/health")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
