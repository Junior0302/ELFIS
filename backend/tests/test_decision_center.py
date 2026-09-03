"""Tests C1.15 — Decision Center Foundation."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.accounting.accounting_models import ElfisAccountingProposal
from app.ai.ai_models import ElfisDocumentAnalysis
from app.dashboard_command_center.router import router as command_router
from app.database import Base, get_db
from app.decision_center.enums import DecisionStatus
from app.decision_center.models import ElfisDecisionItem
from app.decision_center.router import router as decisions_router
from app.decision_center.service import DecisionCenterService
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Organization, OrganizationMember, Role, User
from app.services.auth import ROLE_PERMS


class DecisionCenterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def _fk(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        from app import models_saas  # noqa: F401
        from app.accounting import accounting_models  # noqa: F401
        from app.ai import ai_models  # noqa: F401
        from app.decision_center import models as decision_models  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.org = Organization(id=42, name="CreaLab", platform_status="active")
        self.org_b = Organization(id=99, name="Other", platform_status="active")
        self.role = Role(id=1, name="owner", permissions='["*"]')
        self.user = User(
            id=7,
            email="o@dev.local",
            first_name="Chris",
            last_name="O",
            status="active",
            password_hash="x",
        )
        self.db.add_all([self.org, self.org_b, self.role, self.user])
        self.db.commit()
        self.db.add(OrganizationMember(user_id=7, organization_id=42, role_id=1, status="active"))
        self.db.commit()

        app = FastAPI()
        app.include_router(decisions_router, prefix="/api")
        app.include_router(command_router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        self.permissions = list(ROLE_PERMS.get("owner", ["*"]))

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=42,
                role="owner",
                permissions=self.permissions,
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        app.dependency_overrides[require_active_subscription] = _auth
        self.client = TestClient(app)

        self._access = patch(
            "app.dashboard_command_center.service.get_subscription_access",
            return_value=MagicMock(has_access=True, read_only=False),
        )
        self._access.start()
        self._notif = patch(
            "app.dashboard_command_center.service.NotificationService.get_unread_count",
            return_value=0,
        )
        self._notif.start()
        self._acct = patch(
            "app.dashboard_command_center.service.AccountingService.list_proposals",
            return_value=([], 0),
        )
        self._acct.start()
        self._fin = patch(
            "app.dashboard_command_center.service.FinancialEngine.snapshot",
            return_value={
                "has_data": False,
                "overdue_count": 0,
                "overdue_amount": 0,
                "pending_count": 0,
                "unpaid_amount": 0,
                "documents_to_process": 0,
            },
        )
        self._fin.start()
        self._publish = patch("app.decision_center.service.safe_publish")
        self._publish.start()
        self._audit = patch("app.decision_center.service.write_audit")
        self._audit.start()

    def tearDown(self):
        for p in (self._access, self._notif, self._acct, self._fin, self._publish, self._audit):
            p.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _add_proposal(self, *, proposal_id="prop-1", status="requires_review", requires_review=True, org=42):
        row = ElfisAccountingProposal(
            organization_id=org,
            proposal_id=proposal_id,
            vault_document_id=f"vault-{proposal_id}",
            document_version=1,
            document_type="facture",
            current_stage="review",
            status=status,
            requires_review=requires_review,
            review_reasons=["écart TTC"],
            document_validation={},
            financial_validation={},
            accounting_mapping={},
            quality_summary={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(row)
        self.db.commit()
        return row

    def _add_analysis(self, *, analysis_id="an-1", status="failed", requires_review=False, org=42):
        row = ElfisDocumentAnalysis(
            organization_id=org,
            analysis_id=analysis_id,
            vault_document_id=f"v-{analysis_id}",
            document_version=1,
            status=status,
            requires_review=requires_review,
            ai_execution_ids=[],
        )
        self.db.add(row)
        self.db.commit()
        return row

    def test_create_from_accounting_proposal(self):
        self._add_proposal()
        svc = DecisionCenterService(self.db)
        stats = svc.sync_open_decisions(42)
        self.assertGreaterEqual(stats["created"], 1)
        rows = self.db.query(ElfisDecisionItem).filter(ElfisDecisionItem.organization_id == 42).all()
        self.assertTrue(any(r.decision_type == "accounting_proposal_requires_review" for r in rows))

    def test_create_from_failed_analysis(self):
        self._add_analysis()
        DecisionCenterService(self.db).sync_open_decisions(42)
        rows = self.db.query(ElfisDecisionItem).all()
        self.assertTrue(any(r.decision_type == "document_analysis_failed" for r in rows))

    def test_deduplication(self):
        self._add_proposal()
        svc = DecisionCenterService(self.db)
        svc.sync_open_decisions(42)
        svc.sync_open_decisions(42)
        count = (
            self.db.query(ElfisDecisionItem)
            .filter(ElfisDecisionItem.decision_type == "accounting_proposal_requires_review")
            .count()
        )
        self.assertEqual(count, 1)

    def test_auto_resolve_when_validated(self):
        prop = self._add_proposal()
        svc = DecisionCenterService(self.db)
        svc.sync_open_decisions(42)
        prop.status = "validated"
        prop.requires_review = False
        self.db.add(prop)
        self.db.commit()
        svc.sync_open_decisions(42)
        row = self.db.query(ElfisDecisionItem).one()
        self.assertEqual(row.status, DecisionStatus.RESOLVED)
        self.assertIsNotNone(row.resolved_at)

    def test_no_physical_delete(self):
        self._add_proposal()
        DecisionCenterService(self.db).sync_open_decisions(42)
        row = self.db.query(ElfisDecisionItem).one()
        DecisionCenterService(self.db).dismiss(
            organization_id=42, decision_id=row.id, permissions=["*"], user_id=7
        )
        still = self.db.get(ElfisDecisionItem, row.id)
        self.assertIsNotNone(still)
        self.assertEqual(still.status, DecisionStatus.DISMISSED)

    def test_isolation(self):
        self._add_proposal(org=99, proposal_id="other")
        DecisionCenterService(self.db).sync_open_decisions(42)
        self.assertEqual(self.db.query(ElfisDecisionItem).filter_by(organization_id=42).count(), 0)

    def test_list_api_and_permission_filter(self):
        self._add_proposal()
        res = self.client.get("/api/decisions?status=open")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["total"], 1)

        self.permissions[:] = ["settings.read"]
        res2 = self.client.get("/api/decisions?status=open")
        self.assertEqual(res2.status_code, 200)
        # settings.read alone cannot view accounting decisions
        self.assertEqual(len(res2.json()["items"]), 0)

    def test_dismiss_api(self):
        self._add_proposal()
        DecisionCenterService(self.db).sync_open_decisions(42)
        decision_id = self.db.query(ElfisDecisionItem).one().id
        res = self.client.post(f"/api/decisions/{decision_id}/dismiss")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["decision"]["status"], "dismissed")

    def test_not_found(self):
        res = self.client.get("/api/decisions/missing")
        self.assertEqual(res.status_code, 404)

    def test_command_center_uses_decision_center(self):
        self._add_proposal()
        res = self.client.get("/api/dashboard/command-center")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["ai_insights"]["status"], "ready")
        self.assertLessEqual(len(body["ai_insights"]["insights"]), 3)
        self.assertTrue(body["ai_insights"]["insights"][0]["decision_id"])
        # Pas de doublon Priority accounting-review
        priority_ids = {p["id"] for p in body["priorities"]}
        self.assertNotIn("accounting-review", priority_ids)

    def test_priority_order_blocking_first(self):
        self._add_proposal(proposal_id="p-high", status="requires_review")
        self._add_proposal(
            proposal_id="p-ready", status="ready_for_validation", requires_review=False
        )
        DecisionCenterService(self.db).sync_open_decisions(42)
        top = DecisionCenterService(self.db).insights_for_command_center(
            organization_id=42, permissions=["*"], limit=3
        )
        self.assertTrue(top)
        # high (requires_review) avant medium (ready)
        self.assertEqual(top[0].severity, "high")

    def test_unauthenticated(self):
        def _anon():
            return AuthContext(user=None, organization_id=None, role=None, permissions=[])

        self.client.app.dependency_overrides[get_auth_context] = _anon
        self.assertEqual(self.client.get("/api/decisions").status_code, 401)


if __name__ == "__main__":
    unittest.main()
