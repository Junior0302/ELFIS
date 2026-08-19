"""Tests C1.2 — POST /api/dev/activate-trial."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.billing.billing_models import ElfisSubscription  # noqa: F401
from app.config import settings
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import AuditLog, Organization, Subscription, User
from app.routers.dev_tools import router
from app.services.auth import ROLE_PERMS
from app.services.stripe_billing import _require_stripe
from fastapi import HTTPException


class DevActivateTrialTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.billing import billing_models  # noqa: F401
        from app import models_saas  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.org = Organization(id=42, name="Dev Org", platform_status="active")
        self.db.add(self.org)
        self.user = User(
            id=7,
            email="owner@dev.local",
            first_name="Dev",
            last_name="Owner",
            status="active",
            password_hash="x",
        )
        self.db.add(self.user)
        self.db.commit()

        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        self._auth_permissions = list(ROLE_PERMS.get("owner", ["*"]))
        self._auth_user = self.user
        self._auth_org_id = 42

        def _auth():
            return AuthContext(
                user=self._auth_user,
                organization_id=self._auth_org_id,
                role="owner",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_db] = _db
        self.app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(self.app)

        self._settings_patch = patch.object(settings, "elfis_dev_trial_enabled", True)
        self._settings_patch.start()
        self._env_patch = patch(
            "app.dev_tools.activate_trial.environment_name",
            return_value="development",
        )
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._settings_patch.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _post(self):
        return self.client.post("/api/dev/activate-trial")

    def _get_status(self):
        return self.client.get("/api/dev/trial-status")

    def test_01_development_flag_on_activates(self):
        res = self._post()
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["outcome"], "created")
        self.assertEqual(body["subscription"]["status"], "trialing")
        self.assertTrue(body["subscription"]["access_granted"])

    def test_trial_status_allowed_when_flag_on(self):
        res = self._get_status()
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertTrue(body["allowed"])
        self.assertTrue(body["flag_enabled"])
        self.assertEqual(body["environment"], "development")
        self.assertIsNone(body["reason"])
        self.assertFalse(body["already_active"])

    def test_trial_status_refused_when_flag_off(self):
        with patch.object(settings, "elfis_dev_trial_enabled", False):
            res = self._get_status()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertFalse(body["allowed"])
        self.assertEqual(body["reason"], "dev_trial_disabled")

    def test_production_with_flag_true_still_refused(self):
        with patch(
            "app.dev_tools.activate_trial.environment_name",
            return_value="production",
        ):
            res = self._post()
            status = self._get_status()
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["code"], "dev_trial_environment_forbidden")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["allowed"])
        self.assertEqual(status.json()["reason"], "dev_trial_environment_forbidden")

    def test_trial_status_already_active_after_activation(self):
        self.assertEqual(self._post().status_code, 200)
        res = self._get_status()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["already_active"])
        self.assertTrue(res.json()["allowed"])

    def test_02_test_environment_activates(self):
        with patch(
            "app.dev_tools.activate_trial.environment_name",
            return_value="test",
        ):
            res = self._post()
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["outcome"], "created")
        self.assertTrue(res.json()["subscription"]["access_granted"])

    def test_03_production_refused(self):
        with patch(
            "app.dev_tools.activate_trial.environment_name",
            return_value="production",
        ):
            res = self._post()
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["code"], "dev_trial_environment_forbidden")

    def test_04_staging_and_unknown_refused(self):
        for env in ("staging", "preview", "foobar"):
            with self.subTest(env=env):
                with patch(
                    "app.dev_tools.activate_trial.environment_name",
                    return_value=env,
                ):
                    res = self._post()
                self.assertEqual(res.status_code, 403)
                self.assertEqual(
                    res.json()["detail"]["code"], "dev_trial_environment_forbidden"
                )

    def test_05_flag_disabled_refused(self):
        with patch.object(settings, "elfis_dev_trial_enabled", False):
            res = self._post()
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["code"], "dev_trial_disabled")

    def test_06_unauthenticated_refused(self):
        self._auth_user = None

        def _auth_none():
            return AuthContext(
                user=None,
                organization_id=42,
                role=None,
                permissions=[],
            )

        self.app.dependency_overrides[get_auth_context] = _auth_none
        res = self._post()
        self.assertEqual(res.status_code, 401)

    def test_07_missing_permission_refused(self):
        self._auth_permissions = ["documents.read"]

        def _auth_member():
            return AuthContext(
                user=self.user,
                organization_id=42,
                role="employe",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_auth_context] = _auth_member
        res = self._post()
        self.assertEqual(res.status_code, 403)
        detail = res.json()["detail"]
        self.assertEqual(detail["code"], "permission_denied")

    def test_08_inactive_organization_refused(self):
        self.org.platform_status = "suspended"
        self.db.add(self.org)
        self.db.commit()
        res = self._post()
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["code"], "organization_inactive")

    def test_09_10_11_first_call_trialing_access(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)
        sub = res.json()["subscription"]
        self.assertEqual(sub["status"], "trialing")
        self.assertTrue(sub["access_granted"])
        # has_access sérialisé comme access_granted ; raw_status trialing
        self.assertEqual(sub["raw_status"], "trialing")
        self.assertTrue(sub["is_trial"])
        self.assertIsNotNone(sub["trial_start"])
        self.assertIsNotNone(sub["trial_end"])

    def test_12_13_second_call_idempotent(self):
        first = self._post()
        self.assertEqual(first.status_code, 200)
        trial_end = first.json()["subscription"]["trial_end"]
        first_id = first.json()["subscription"]["id"]

        second = self._post()
        self.assertEqual(second.status_code, 200)
        body = second.json()
        self.assertEqual(body["outcome"], "already_active")
        self.assertEqual(body["subscription"]["trial_end"], trial_end)
        self.assertEqual(body["subscription"]["id"], first_id)

        count = self.db.query(Subscription).filter(Subscription.organization_id == 42).count()
        self.assertEqual(count, 1)

        row = self.db.query(Subscription).filter(Subscription.organization_id == 42).one()
        original_start = row.trial_start
        original_end = row.trial_end
        self._post()
        self.db.refresh(row)
        self.assertEqual(row.trial_start, original_start)
        self.assertEqual(row.trial_end, original_end)

    def test_14_legacy_and_elfis_sync(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)
        legacy = (
            self.db.query(Subscription).filter(Subscription.organization_id == 42).one()
        )
        self.assertEqual(legacy.status, "trialing")
        self.assertIsNone(legacy.stripe_subscription_id)

        elfis = (
            self.db.query(ElfisSubscription)
            .filter(
                ElfisSubscription.organization_id == 42,
                ElfisSubscription.is_current.is_(True),
            )
            .first()
        )
        self.assertIsNotNone(elfis)
        self.assertEqual(elfis.status, "trialing")
        self.assertEqual(elfis.legacy_subscription_id, legacy.id)

    def test_15_audit_event_created(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)
        logs = (
            self.db.query(AuditLog)
            .filter(AuditLog.organization_id == 42, AuditLog.module == "dev_tools")
            .all()
        )
        self.assertTrue(logs)
        self.assertTrue(
            any(log.action.startswith("developer_trial_activated:created") for log in logs)
        )

        res2 = self._post()
        self.assertEqual(res2.status_code, 200)
        logs2 = (
            self.db.query(AuditLog)
            .filter(AuditLog.organization_id == 42, AuditLog.module == "dev_tools")
            .all()
        )
        self.assertTrue(
            any(
                log.action.startswith("developer_trial_activated:already_active")
                for log in logs2
            )
        )

    def test_16_stripe_require_unchanged(self):
        """Le garde Stripe réel reste inchangé (503 si non configuré)."""
        with (
            patch.object(settings, "stripe_secret_key", ""),
            patch.object(settings, "stripe_price_pro", ""),
        ):
            with self.assertRaises(HTTPException) as ctx:
                _require_stripe()
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertEqual(ctx.exception.detail["code"], "stripe_not_configured")

    def test_active_subscription_idempotent_no_extend(self):
        end = datetime.utcnow() + timedelta(days=20)
        start = datetime.utcnow() - timedelta(days=5)
        self.db.add(
            Subscription(
                organization_id=42,
                plan="pro",
                status="active",
                price=19.0,
                trial_start=start,
                trial_end=end,
                current_period_start=start,
                current_period_end=end,
            )
        )
        self.db.commit()
        res = self._post()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["outcome"], "already_active")
        row = self.db.query(Subscription).filter(Subscription.organization_id == 42).one()
        self.assertEqual(row.status, "active")
        self.assertEqual(row.trial_end, end)

    def test_admin_revoked_incompatible(self):
        self.db.add(
            Subscription(
                organization_id=42,
                plan="pro",
                status="active",
                price=19.0,
                admin_revoked_at=datetime.utcnow(),
                admin_revoked_reason_public="fraude",
            )
        )
        self.db.commit()
        res = self._post()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["detail"]["code"], "subscription_incompatible")


if __name__ == "__main__":
    unittest.main()
