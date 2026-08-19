"""S1.6.1 Proposal → Invoice bridge tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.events.event_types import EventNames
from app.models_saas import Customer, Organization, SalesDocument, User
from app.sales_crm.service import create_company, create_opportunity, create_person
from app.sales_proposals.enums import ProposalStatus
from app.sales_proposals.router import router
from app.sales_proposals.service import ProposalService
from app.services.auth import ROLE_PERMS


class ProposalInvoiceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.sales_crm import models as sales_models  # noqa: F401
        from app.sales_proposals import models as prop_models  # noqa: F401
        from app import models_saas  # noqa: F401
        from app import models_vault  # noqa: F401
        from app.events import event_models  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(Organization(id=1, name="Org A"))
        self.db.add(Organization(id=2, name="Org B"))
        self.user = User(
            id=1,
            email="owner@test.local",
            first_name="Owner",
            last_name="Test",
            status="active",
            password_hash="x",
        )
        self.db.add(self.user)
        self.db.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        self._permissions = list(ROLE_PERMS.get("owner", ["*"]))
        self._org_id = 1

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=self._org_id,
                role="owner",
                permissions=list(self._permissions),
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(app)
        self._publish_patcher = patch("app.sales_proposals.events.safe_publish")
        self._archive_patcher = patch("app.sales_proposals.service.archive_or_reuse_pdf")
        self.publish = self._publish_patcher.start()
        archive = self._archive_patcher.start()
        vault_doc = MagicMock()
        vault_doc.id = 99
        vault_doc.checksum_sha256 = "abc"
        archive.return_value = (vault_doc, False)

    def tearDown(self):
        self._publish_patcher.stop()
        self._archive_patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _accepted_proposal(self) -> int:
        company = create_company(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "name": "Bridge Co",
                "email": "billing@bridge.test",
                "siret": "12345678900099",
                "address_line": "2 rue Bridge",
                "city": "Lyon",
                "postal_code": "69001",
            },
        )
        person = create_person(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "first_name": "Bob",
                "last_name": "Builder",
                "company_id": company.id,
                "email": "bob@bridge.test",
            },
        )
        opp = create_opportunity(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "name": "Deal Bridge",
                "estimated_amount": Decimal("500"),
                "company_id": company.id,
                "person_id": person.id,
                "probability": 80,
            },
        )
        from app.sales_crm.deal_service import add_product

        add_product(
            self.db,
            organization_id=1,
            user_id=1,
            opportunity_id=opp.id,
            data={
                "name": "Service",
                "quantity": "1",
                "unit_price": "500",
                "discount_percent": "0",
            },
        )
        self.db.commit()

        created = self.client.post(
            "/api/sales/proposals",
            json={
                "opportunity_id": opp.id,
                "proposal_type": "quote",
                "title": "Offre Bridge",
                "seed_from_opportunity_products": True,
                "valid_until": (date.today() + timedelta(days=30)).isoformat(),
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        proposal_id = created.json()["id"]

        svc = ProposalService(self.db)
        proposal = svc._get_proposal(1, proposal_id)
        version = svc._get_current_version(proposal)
        version.payment_terms = "30 jours"
        version.terms = "CGV"
        version.introduction = "Intro"
        version.tax_total = Decimal("100.00")  # may be recomputed
        self.db.commit()
        svc._recompute_version_totals(version)
        svc._refresh_readiness(proposal, version)
        self.db.commit()

        for action in ("prepare", "request-review", "approve"):
            res = self.client.post(f"/api/sales/proposals/{proposal_id}/{action}")
            self.assertEqual(res.status_code, 200, f"{action}: {res.text}")

        pdf = self.client.post(f"/api/sales/proposals/{proposal_id}/generate-pdf")
        self.assertEqual(pdf.status_code, 200, pdf.text)
        sent = self.client.post(f"/api/sales/proposals/{proposal_id}/mark-sent")
        self.assertEqual(sent.status_code, 200, sent.text)
        viewed = self.client.post(f"/api/sales/proposals/{proposal_id}/mark-viewed")
        self.assertEqual(viewed.status_code, 200, viewed.text)
        accepted = self.client.post(f"/api/sales/proposals/{proposal_id}/accept")
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["status"], ProposalStatus.accepted.value)
        return proposal_id

    def test_requires_accepted(self):
        company = create_company(
            self.db,
            organization_id=1,
            user_id=1,
            data={"name": "Draft Co", "email": "d@t.test"},
        )
        created = self.client.post(
            "/api/sales/proposals",
            json={"sales_company_id": company.id, "title": "Draft"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        pid = created.json()["id"]
        conv = self.client.post(
            f"/api/sales/proposals/{pid}/convert-to-invoice",
            json={"customer_resolution_mode": "create_new_customer", "customer_payload": {"name": "X"}},
        )
        self.assertEqual(conv.status_code, 409)

    def test_convert_create_customer_draft_idempotent(self):
        proposal_id = self._accepted_proposal()

        state = self.client.get(f"/api/sales/proposals/{proposal_id}/conversion-state")
        self.assertEqual(state.status_code, 200, state.text)
        self.assertIn(state.json()["conversion_status"], ("customer_required", "ready", "customer_ambiguous"))

        preview = self.client.post(f"/api/sales/proposals/{proposal_id}/conversion-preview")
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertFalse(preview.json()["can_confirm"])  # no customer yet

        convert = self.client.post(
            f"/api/sales/proposals/{proposal_id}/convert-to-invoice",
            json={
                "customer_resolution_mode": "create_new_customer",
                "customer_payload": {
                    "name": "Bridge Co Facture",
                    "email": "billing@bridge.test",
                },
                "idempotency_key": "bridge-key-1",
            },
        )
        self.assertEqual(convert.status_code, 200, convert.text)
        body = convert.json()
        self.assertFalse(body["already_converted"])
        self.assertEqual(body["invoice_status"], "draft")
        invoice_id = body["invoice_id"]

        invoice = self.db.get(SalesDocument, invoice_id)
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.status, "draft")
        self.assertEqual(invoice.doc_type, "facture")
        self.assertEqual(invoice.source_type, "sales_proposal")
        self.assertEqual(invoice.source_id, str(proposal_id))

        # Idempotence
        again = self.client.post(
            f"/api/sales/proposals/{proposal_id}/convert-to-invoice",
            json={
                "customer_resolution_mode": "use_linked_customer",
                "idempotency_key": "bridge-key-1",
            },
        )
        self.assertEqual(again.status_code, 200, again.text)
        self.assertTrue(again.json()["already_converted"])
        self.assertEqual(again.json()["invoice_id"], invoice_id)

        # Only one invoice
        count = (
            self.db.query(SalesDocument)
            .filter(
                SalesDocument.organization_id == 1,
                SalesDocument.source_type == "sales_proposal",
                SalesDocument.source_id == str(proposal_id),
            )
            .count()
        )
        self.assertEqual(count, 1)

        proposal = ProposalService(self.db)._get_proposal(1, proposal_id)
        self.assertEqual(proposal.status, ProposalStatus.converted.value)
        self.assertEqual(proposal.linked_invoice_id, invoice_id)

        names = [c.args[1].event_name for c in self.publish.call_args_list]
        self.assertIn(EventNames.SALES_PROPOSAL_CONVERTED, names)
        self.assertIn(EventNames.BILLING_INVOICE_CREATED_FROM_PROPOSAL, names)

    def test_foreign_customer_rejected(self):
        proposal_id = self._accepted_proposal()
        foreign = Customer(organization_id=2, name="Other Org", email="x@y.z")
        self.db.add(foreign)
        self.db.commit()

        res = self.client.post(
            f"/api/sales/proposals/{proposal_id}/conversion/customer",
            json={
                "customer_resolution_mode": "use_existing_customer",
                "customer_id": foreign.id,
            },
        )
        self.assertEqual(res.status_code, 403)

    def test_existing_customer_convert(self):
        proposal_id = self._accepted_proposal()
        customer = Customer(
            organization_id=1,
            name="Bridge Co",
            email="billing@bridge.test",
            phone="",
            address="",
            vat_number="",
        )
        self.db.add(customer)
        self.db.commit()

        link = self.client.post(
            f"/api/sales/proposals/{proposal_id}/conversion/customer",
            json={
                "customer_resolution_mode": "use_existing_customer",
                "customer_id": customer.id,
            },
        )
        self.assertEqual(link.status_code, 200, link.text)

        preview = self.client.post(
            f"/api/sales/proposals/{proposal_id}/conversion-preview?customer_id={customer.id}"
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertTrue(preview.json()["can_confirm"])

        convert = self.client.post(
            f"/api/sales/proposals/{proposal_id}/convert-to-invoice",
            json={
                "customer_resolution_mode": "use_linked_customer",
                "idempotency_key": "existing-1",
            },
        )
        self.assertEqual(convert.status_code, 200, convert.text)
        self.assertEqual(convert.json()["invoice_status"], "draft")

    def test_permission_convert_requires_invoice_create(self):
        proposal_id = self._accepted_proposal()
        self._permissions = ["sales.proposals.read", "sales.proposals.convert"]
        res = self.client.post(
            f"/api/sales/proposals/{proposal_id}/convert-to-invoice",
            json={
                "customer_resolution_mode": "create_new_customer",
                "customer_payload": {"name": "No Invoice Perm"},
            },
        )
        self.assertEqual(res.status_code, 403)

    def test_workspace_actions_converted(self):
        proposal_id = self._accepted_proposal()
        self.client.post(
            f"/api/sales/proposals/{proposal_id}/convert-to-invoice",
            json={
                "customer_resolution_mode": "create_new_customer",
                "customer_payload": {"name": "Actions Co"},
                "idempotency_key": "actions-1",
            },
        )
        ws = self.client.get(f"/api/sales/proposals/{proposal_id}/workspace")
        self.assertEqual(ws.status_code, 200, ws.text)
        actions = {a["id"]: a for a in ws.json()["available_actions"]}
        self.assertFalse(actions["convert_to_invoice"]["enabled"])
        self.assertTrue(actions["open_linked_invoice"]["enabled"])

    def test_multi_vat_blocked_on_preview_and_convert(self):
        """Option B PR1.1 — jamais de TVA silencieuse au taux de la 1ʳᵉ ligne."""
        company = create_company(
            self.db,
            organization_id=1,
            user_id=1,
            data={"name": "Multi VAT Co", "email": "mv@bridge.test"},
        )
        person = create_person(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "first_name": "Vat",
                "last_name": "Tester",
                "company_id": company.id,
                "email": "vat@bridge.test",
            },
        )
        opp = create_opportunity(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "name": "Deal Multi VAT",
                "estimated_amount": Decimal("1000"),
                "company_id": company.id,
                "person_id": person.id,
            },
        )
        self.db.commit()
        created = self.client.post(
            "/api/sales/proposals",
            json={
                "opportunity_id": opp.id,
                "title": "Multi VAT",
                "seed_from_opportunity_products": False,
                "valid_until": (date.today() + timedelta(days=30)).isoformat(),
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        proposal_id = created.json()["id"]

        line_a = self.client.post(
            f"/api/sales/proposals/{proposal_id}/lines",
            json={"name": "Ligne 20%", "quantity": "1", "unit_price": "100", "tax_rate": "20"},
        )
        self.assertEqual(line_a.status_code, 201, line_a.text)
        line_b = self.client.post(
            f"/api/sales/proposals/{proposal_id}/lines",
            json={"name": "Ligne 5.5%", "quantity": "1", "unit_price": "100", "tax_rate": "5.5"},
        )
        self.assertEqual(line_b.status_code, 201, line_b.text)

        svc = ProposalService(self.db)
        proposal = svc._get_proposal(1, proposal_id)
        version = svc._get_current_version(proposal)
        version.payment_terms = "30 jours"
        version.terms = "CGV"
        version.introduction = "Intro"
        svc._recompute_version_totals(version)
        svc._refresh_readiness(proposal, version)
        self.db.commit()

        for action in ("prepare", "request-review", "approve"):
            res = self.client.post(f"/api/sales/proposals/{proposal_id}/{action}")
            self.assertEqual(res.status_code, 200, f"{action}: {res.text}")
        pdf = self.client.post(f"/api/sales/proposals/{proposal_id}/generate-pdf")
        self.assertEqual(pdf.status_code, 200, pdf.text)
        self.assertEqual(self.client.post(f"/api/sales/proposals/{proposal_id}/mark-sent").status_code, 200)
        self.assertEqual(self.client.post(f"/api/sales/proposals/{proposal_id}/mark-viewed").status_code, 200)
        accepted = self.client.post(f"/api/sales/proposals/{proposal_id}/accept")
        self.assertEqual(accepted.status_code, 200, accepted.text)

        customer = Customer(
            organization_id=1,
            name="Multi VAT Co",
            email="mv@bridge.test",
            phone="",
            address="",
            vat_number="",
        )
        self.db.add(customer)
        self.db.commit()
        self.client.post(
            f"/api/sales/proposals/{proposal_id}/conversion/customer",
            json={
                "customer_resolution_mode": "use_existing_customer",
                "customer_id": customer.id,
            },
        )

        preview = self.client.post(
            f"/api/sales/proposals/{proposal_id}/conversion-preview?customer_id={customer.id}"
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        body = preview.json()
        self.assertFalse(body["can_confirm"])
        blockers = " ".join(body.get("blockers") or [])
        self.assertIn("multi-taux", blockers.lower())
        rates = body.get("multi_vat_rates") or []
        self.assertGreaterEqual(len(rates), 2)

        convert = self.client.post(
            f"/api/sales/proposals/{proposal_id}/convert-to-invoice",
            json={
                "customer_resolution_mode": "use_linked_customer",
                "idempotency_key": "multi-vat-1",
            },
        )
        self.assertEqual(convert.status_code, 409, convert.text)
        detail = convert.json().get("detail") or {}
        if isinstance(detail, dict):
            self.assertEqual(detail.get("code"), "multi_vat_unsupported")
        else:
            self.assertIn("multi_vat", str(detail).lower() + convert.text.lower())


if __name__ == "__main__":
    unittest.main()
