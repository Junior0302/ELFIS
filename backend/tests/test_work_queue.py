"""Tests C1.17 — Work Queue."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.accounting.accounting_models import ElfisAccountingProposal
from app.ai.ai_models import ElfisDocumentAnalysis
from app.dashboard_command_center.router import router as command_router
from app.database import Base, get_db
from app.decision_center.enums import DecisionExecutionStatus, DecisionStatus
from app.decision_center.models import ElfisDecisionItem
from app.decision_center.router import router as decisions_router
from app.decision_center.service import DecisionCenterService
from app.deps import AuthContext, get_auth_context
from app.models_saas import Organization, OrganizationMember, Role, User
from app.services.auth import ROLE_PERMS
from app.work_queue.buckets import resolve_work_queue_bucket
from app.work_queue.enums import WorkQueueBucket
from app.work_queue.router import router as work_queue_router


class WorkQueueTests(unittest.TestCase):
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
            id=7, email="wq@dev.local", first_name="W", last_name="Q", status="active", password_hash="x"
        )
        self.db.add_all([self.org, self.org_b, self.role, self.user])
        self.db.commit()
        self.db.add(OrganizationMember(user_id=7, organization_id=42, role_id=1, status="active"))
        self.db.commit()

        app = FastAPI()
        app.include_router(work_queue_router, prefix="/api")
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
                user=self.user, organization_id=42, role="owner", permissions=self.permissions
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(app)
        self.app = app

        self._publish = patch("app.decision_center.service.safe_publish")
        self._publish.start()
        self._publish_wq = patch("app.work_queue.service.safe_publish")
        self._publish_wq.start()
        self._audit = patch("app.decision_center.service.write_audit")
        self._audit.start()
        self._audit_wq = patch("app.work_queue.service.write_audit")
        self._audit_wq.start()
        self._access = patch(
            "app.dashboard_command_center.service.get_subscription_access",
            return_value=__import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(
                has_access=True, read_only=False
            ),
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

    def tearDown(self):
        for p in (
            self._publish,
            self._publish_wq,
            self._audit,
            self._audit_wq,
            self._access,
            self._notif,
            self._acct,
            self._fin,
        ):
            p.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _add_proposal(self, *, proposal_id="prop-1", status="requires_review", requires_review=True):
        row = ElfisAccountingProposal(
            organization_id=42,
            proposal_id=proposal_id,
            vault_document_id=f"vault-{proposal_id}",
            document_version=1,
            document_type="facture",
            current_stage="review",
            status=status,
            requires_review=requires_review,
            review_reasons=["écart"],
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

    def _sync(self):
        DecisionCenterService(self.db).sync_open_decisions(42)

    def test_bucket_mapping_unique(self):
        self._add_proposal()
        self._sync()
        row = self.db.query(ElfisDecisionItem).one()
        self.assertEqual(resolve_work_queue_bucket(row), WorkQueueBucket.TODO)
        row.status = DecisionStatus.IN_PROGRESS
        self.assertEqual(resolve_work_queue_bucket(row), WorkQueueBucket.IN_PROGRESS)
        row.execution_status = DecisionExecutionStatus.RUNNING
        self.assertEqual(resolve_work_queue_bucket(row), WorkQueueBucket.IN_PROGRESS)
        row.status = DecisionStatus.OPEN
        row.execution_status = DecisionExecutionStatus.SUCCEEDED
        row.last_action_type = "retry_document_analysis"
        self.assertEqual(resolve_work_queue_bucket(row), WorkQueueBucket.WAITING)
        row.status = DecisionStatus.RESOLVED
        self.assertEqual(resolve_work_queue_bucket(row), WorkQueueBucket.COMPLETED)

    def test_queue_todo_and_counts(self):
        self._add_proposal()
        self._add_proposal(proposal_id="prop-2", status="ready_for_validation", requires_review=False)
        res = self.client.get("/api/work-queue?bucket=todo&sync=true")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertGreaterEqual(body["counts"]["todo"], 2)
        self.assertEqual(body["filters"]["bucket"], "todo")
        self.assertTrue(all(i["bucket"] == "todo" for i in body["items"]))

    def test_start_idempotent(self):
        self._add_proposal()
        self._sync()
        decision_id = self.db.query(ElfisDecisionItem).one().id
        r1 = self.client.post(f"/api/decisions/{decision_id}/start")
        r2 = self.client.post(f"/api/decisions/{decision_id}/start")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["status"], "in_progress")
        self.assertEqual(r2.json()["status"], "in_progress")
        body = self.client.get("/api/work-queue?bucket=in_progress").json()
        self.assertGreaterEqual(body["counts"]["in_progress"], 1)

    def test_start_resolved_refused(self):
        self._add_proposal()
        self._sync()
        row = self.db.query(ElfisDecisionItem).one()
        row.status = DecisionStatus.RESOLVED
        self.db.add(row)
        self.db.commit()
        res = self.client.post(f"/api/decisions/{row.id}/start")
        self.assertEqual(res.status_code, 409)

    def test_search_and_isolation(self):
        self._add_proposal(proposal_id="alpha-prop")
        self._sync()
        # autre org
        self.db.add(
            ElfisAccountingProposal(
                organization_id=99,
                proposal_id="secret",
                vault_document_id="v-secret",
                document_version=1,
                document_type="facture",
                current_stage="review",
                status="requires_review",
                requires_review=True,
                review_reasons=[],
                document_validation={},
                financial_validation={},
                accounting_mapping={},
                quality_summary={},
            )
        )
        self.db.commit()
        DecisionCenterService(self.db).sync_open_decisions(99)
        res = self.client.get("/api/work-queue?bucket=todo&search=secret")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["pagination"]["total_items"], 0)
        res2 = self.client.get("/api/work-queue?bucket=todo&search=alpha")
        self.assertGreaterEqual(res2.json()["pagination"]["total_items"], 1)

    def test_waiting_reason(self):
        self._add_proposal()
        self._sync()
        row = self.db.query(ElfisDecisionItem).one()
        row.last_action_type = "retry_document_analysis"
        row.execution_status = DecisionExecutionStatus.SUCCEEDED
        self.db.add(row)
        self.db.commit()
        body = self.client.get("/api/work-queue?bucket=waiting").json()
        self.assertGreaterEqual(body["counts"]["waiting"], 1)
        self.assertTrue(body["items"][0]["waiting_reason"]["label"])

    def test_completed_window(self):
        self._add_proposal()
        self._sync()
        row = self.db.query(ElfisDecisionItem).one()
        row.status = DecisionStatus.DISMISSED
        row.dismissed_at = datetime.utcnow() - timedelta(days=60)
        row.updated_at = row.dismissed_at
        self.db.add(row)
        self.db.commit()
        body = self.client.get("/api/work-queue?bucket=completed").json()
        self.assertEqual(body["counts"]["completed"], 0)

    def test_command_center_todo_only(self):
        self._add_proposal()
        self._sync()
        decision_id = self.db.query(ElfisDecisionItem).one().id
        self.client.post(f"/api/decisions/{decision_id}/start")
        # create another todo
        self._add_proposal(proposal_id="prop-todo-2")
        res = self.client.get("/api/dashboard/command-center")
        self.assertEqual(res.status_code, 200)
        ai = res.json()["ai_insights"]
        self.assertIn("counts", ai)
        self.assertLessEqual(len(ai["insights"]), 3)
        for insight in ai["insights"]:
            # only todo — started one must not appear as new insight
            self.assertNotEqual(insight["decision_id"], decision_id)
        self.assertEqual(ai["work_queue_path"], "/work-queue")

    def test_permission_filter(self):
        self._add_proposal()
        self.permissions[:] = ["settings.read"]
        body = self.client.get("/api/work-queue?bucket=todo&sync=true").json()
        self.assertEqual(body["counts"]["todo"], 0)


if __name__ == "__main__":
    unittest.main()
