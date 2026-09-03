"""Tests C1.16 — Decision Execution Layer."""

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
from app.database import Base, get_db
from app.decision_center.enums import DecisionStatus
from app.decision_center.models import ElfisDecisionExecutionAttempt, ElfisDecisionItem
from app.decision_center.router import router as decisions_router
from app.decision_center.service import DecisionCenterService
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Organization, OrganizationMember, Role, User
from app.services.auth import ROLE_PERMS


class DecisionExecutionTests(unittest.TestCase):
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
            email="exec@dev.local",
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
        self.app = app

        self._publish = patch("app.decision_center.service.safe_publish")
        self._publish.start()
        self._publish_ex = patch("app.decision_center.execution.safe_publish")
        self._publish_ex.start()
        self._audit = patch("app.decision_center.service.write_audit")
        self._audit.start()
        self._audit_ex = patch("app.decision_center.execution.write_audit")
        self._audit_ex.start()

    def tearDown(self):
        for p in (self._publish, self._publish_ex, self._audit, self._audit_ex):
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
            review_reasons=["écart TTC"],
            financial_validation={"difference": 12.5, "detected_ttc": 100, "expected_ttc": 112.5},
            document_validation={},
            accounting_mapping={},
            quality_summary={},
            amount_ttc=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(row)
        self.db.commit()
        return row

    def _add_analysis(self, *, analysis_id="an-1", status="failed"):
        row = ElfisDocumentAnalysis(
            organization_id=42,
            analysis_id=analysis_id,
            vault_document_id=f"v-{analysis_id}",
            document_version=1,
            status=status,
            requires_review=False,
            current_stage="classification",
            ai_execution_ids=[],
        )
        self.db.add(row)
        self.db.commit()
        return row

    def _decision_id(self) -> str:
        DecisionCenterService(self.db).sync_open_decisions(42)
        return self.db.query(ElfisDecisionItem).filter_by(organization_id=42).first().id

    def test_detail_with_evidence(self):
        self._add_proposal()
        decision_id = self._decision_id()
        res = self.client.get(f"/api/decisions/{decision_id}")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["evidence"])
        self.assertTrue(any(e["type"] == "source_status" for e in body["evidence"]))
        self.assertTrue(any(e["type"] == "financial_difference" for e in body["evidence"]))
        self.assertIn("what_to_do", body)
        types = {a["action_type"] for a in body["available_actions"]}
        self.assertIn("open_accounting_proposal", types)
        self.assertIn("validate_accounting_proposal", types)
        self.assertIn("dismiss", types)

    def test_undeclared_action_rejected(self):
        self._add_proposal()
        decision_id = self._decision_id()
        res = self.client.post(f"/api/decisions/{decision_id}/actions/hack_the_planet", json={})
        self.assertEqual(res.status_code, 400)

    def test_other_org_denied(self):
        self._add_proposal()
        decision_id = self._decision_id()

        def _other():
            return AuthContext(
                user=self.user,
                organization_id=99,
                role="owner",
                permissions=["*"],
            )

        self.app.dependency_overrides[get_auth_context] = _other
        res = self.client.get(f"/api/decisions/{decision_id}")
        self.assertEqual(res.status_code, 404)

    def test_permission_insufficient(self):
        self._add_proposal()
        decision_id = self._decision_id()
        self.permissions[:] = ["settings.read"]
        res = self.client.get(f"/api/decisions/{decision_id}")
        self.assertEqual(res.status_code, 403)

    def test_action_on_resolved_refused(self):
        self._add_proposal()
        decision_id = self._decision_id()
        row = self.db.get(ElfisDecisionItem, decision_id)
        row.status = DecisionStatus.RESOLVED
        self.db.add(row)
        self.db.commit()
        res = self.client.post(
            f"/api/decisions/{decision_id}/actions/open_accounting_proposal", json={}
        )
        self.assertEqual(res.status_code, 409)

    def test_action_on_dismissed_refused(self):
        self._add_proposal()
        decision_id = self._decision_id()
        row = self.db.get(ElfisDecisionItem, decision_id)
        row.status = DecisionStatus.DISMISSED
        self.db.add(row)
        self.db.commit()
        res = self.client.post(
            f"/api/decisions/{decision_id}/actions/open_accounting_proposal", json={}
        )
        self.assertEqual(res.status_code, 409)

    def test_navigate_creates_attempt(self):
        self._add_proposal()
        decision_id = self._decision_id()
        res = self.client.post(
            f"/api/decisions/{decision_id}/actions/open_accounting_proposal",
            json={"idempotency_key": "nav-1"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["result"]["status"], "succeeded")
        self.assertTrue(body["result"]["navigation_path"].startswith("/accounting/proposals/"))
        self.assertEqual(
            self.db.query(ElfisDecisionExecutionAttempt).filter_by(decision_id=decision_id).count(),
            1,
        )
        self.assertEqual(body["decision"]["status"], "in_progress")

    def test_validate_delegates_and_can_resolve(self):
        self._add_proposal(status="ready_for_validation", requires_review=False)
        decision_id = self._decision_id()
        with patch(
            "app.decision_center.execution.AccountingService.validate_proposal",
            return_value=MagicMock(),
        ) as mocked:
            # Après validation simulée, marquer la proposition comme validated pour sync
            def _side_effect(**kwargs):
                prop = (
                    self.db.query(ElfisAccountingProposal)
                    .filter_by(proposal_id="prop-1")
                    .one()
                )
                prop.status = "validated"
                prop.requires_review = False
                self.db.add(prop)
                self.db.flush()
                return MagicMock()

            mocked.side_effect = _side_effect
            res = self.client.post(
                f"/api/decisions/{decision_id}/actions/validate_accounting_proposal",
                json={
                    "idempotency_key": "val-1",
                    "confirm_balanced_entry": True,
                    "confirm_document_reviewed": True,
                },
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["decision"]["status"], "resolved")
        self.assertEqual(
            self.db.query(ElfisDecisionExecutionAttempt)
            .filter_by(decision_id=decision_id, status="succeeded")
            .count(),
            1,
        )

    def test_idempotence(self):
        self._add_proposal()
        decision_id = self._decision_id()
        payload = {"idempotency_key": "same-key"}
        with patch(
            "app.decision_center.execution.AccountingService.validate_proposal",
            return_value=MagicMock(),
        ) as mocked:
            r1 = self.client.post(
                f"/api/decisions/{decision_id}/actions/validate_accounting_proposal",
                json={
                    **payload,
                    "confirm_balanced_entry": True,
                    "confirm_document_reviewed": True,
                },
            )
            r2 = self.client.post(
                f"/api/decisions/{decision_id}/actions/validate_accounting_proposal",
                json={
                    **payload,
                    "confirm_balanced_entry": True,
                    "confirm_document_reviewed": True,
                },
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(mocked.call_count, 1)

    def test_retry_document_analysis(self):
        self._add_analysis()
        decision_id = self._decision_id()
        accepted = MagicMock(
            reused_existing_analysis=False,
            status="pending",
        )
        with patch(
            "app.decision_center.execution.DocumentAnalysisService.start_analysis",
            return_value=accepted,
        ) as mocked:
            res = self.client.post(
                f"/api/decisions/{decision_id}/actions/retry_document_analysis",
                json={"idempotency_key": "retry-1"},
            )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Analyse", res.json()["result"]["message"])
        mocked.assert_called_once()

    def test_no_resolve_if_cause_persists(self):
        self._add_proposal(status="ready_for_validation", requires_review=False)
        decision_id = self._decision_id()
        with patch(
            "app.decision_center.execution.AccountingService.validate_proposal",
            return_value=MagicMock(),
        ):
            # Ne change pas le statut source → cause toujours présente
            res = self.client.post(
                f"/api/decisions/{decision_id}/actions/validate_accounting_proposal",
                json={
                    "idempotency_key": "val-persist",
                    "confirm_balanced_entry": True,
                    "confirm_document_reviewed": True,
                },
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["decision"]["status"], "in_progress")

    def test_history_present(self):
        self._add_proposal()
        decision_id = self._decision_id()
        self.client.post(
            f"/api/decisions/{decision_id}/actions/open_accounting_proposal",
            json={},
        )
        body = self.client.get(f"/api/decisions/{decision_id}?sync=false").json()
        kinds = {h["kind"] for h in body["history"]}
        self.assertIn("created", kinds)
        self.assertTrue(any(k.startswith("execution_") for k in kinds))


if __name__ == "__main__":
    unittest.main()
