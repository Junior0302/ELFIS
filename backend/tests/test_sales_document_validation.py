"""Validation métier POST/PATCH /api/billing/documents (P1 bêta readiness)."""

from __future__ import annotations

import unittest
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Customer, Organization, OrganizationMember, Role, SalesDocument, User
from app.routers import billing as billing_router
from app.services.auth import create_access_token
from app.services.billing import create_sales_document
from app.services.sales_document_validation import (
    SalesDocumentValidationError,
    validate_sales_document_payload,
)


def _valid_line(**overrides):
    base = {"label": "Prestation", "quantity": 1, "unit_price": 100.0}
    base.update(overrides)
    return base


class SalesDocumentValidationUnitTests(unittest.TestCase):
    def test_rejects_empty_customer_and_lines(self):
        with self.assertRaises(SalesDocumentValidationError) as ctx:
            validate_sales_document_payload(
                doc_type="facture",
                customer_name="",
                customer_id=None,
                amount_ht=0,
                vat_rate=20,
                lines=[],
            )
        self.assertEqual(ctx.exception.code, "customer_required")

    def test_rejects_missing_lines(self):
        with self.assertRaises(SalesDocumentValidationError) as ctx:
            validate_sales_document_payload(
                doc_type="facture",
                customer_name="Client SA",
                customer_id=None,
                amount_ht=100,
                vat_rate=20,
                lines=[],
            )
        self.assertEqual(ctx.exception.code, "lines_required")

    def test_rejects_invalid_quantity(self):
        with self.assertRaises(SalesDocumentValidationError) as ctx:
            validate_sales_document_payload(
                doc_type="facture",
                customer_name="Client SA",
                customer_id=None,
                amount_ht=100,
                vat_rate=20,
                lines=[_valid_line(quantity=0)],
            )
        self.assertEqual(ctx.exception.code, "invalid_line_quantity")

    def test_rejects_negative_unit_price(self):
        with self.assertRaises(SalesDocumentValidationError) as ctx:
            validate_sales_document_payload(
                doc_type="devis",
                customer_name="Prospect",
                customer_id=None,
                amount_ht=10,
                vat_rate=20,
                lines=[_valid_line(unit_price=-5)],
            )
        self.assertEqual(ctx.exception.code, "invalid_line_price")

    def test_allows_zero_ht_with_free_line(self):
        validate_sales_document_payload(
            doc_type="facture",
            customer_name="Client SA",
            customer_id=None,
            amount_ht=0,
            vat_rate=20,
            lines=[_valid_line(unit_price=0)],
        )

    def test_allows_devis_with_valid_payload(self):
        validate_sales_document_payload(
            doc_type="devis",
            customer_name="Prospect",
            customer_id=None,
            amount_ht=50,
            vat_rate=20,
            lines=[_valid_line(unit_price=50)],
        )


class SalesDocumentValidationApiTests(unittest.TestCase):
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

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.org = Organization(id=1, name="Org A", platform_status="active")
        self.role = Role(id=1, name="owner", permissions='["*"]')
        self.user = User(
            id=10,
            email="owner@a.local",
            first_name="Ada",
            last_name="Owner",
            status="active",
            password_hash="x",
        )
        self.customer = Customer(
            organization_id=1,
            name="Client CRM",
            email="client@example.test",
            created_at=datetime.utcnow(),
        )
        self.db.add_all([self.org, self.role, self.user, self.customer])
        self.db.commit()
        self.db.add(
            OrganizationMember(
                user_id=10,
                organization_id=1,
                role_id=1,
                status="active",
            )
        )
        self.db.commit()

        app = FastAPI()
        app.include_router(billing_router.router, prefix="/api")

        def _db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=1,
                role="owner",
                permissions={"*"},
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        app.dependency_overrides[require_active_subscription] = lambda: None

        self.client = TestClient(app)
        self.headers = {
            "Authorization": f"Bearer {create_access_token({'sub': '10', 'org_id': 1})}",
            "X-Organization-Id": "1",
        }

    def tearDown(self):
        self.db.close()

    def _post(self, payload: dict):
        return self.client.post("/api/billing/documents", headers=self.headers, json=payload)

    def test_api_rejects_empty_invoice(self):
        r = self._post(
            {
                "doc_type": "facture",
                "customer_name": "",
                "amount_ht": 0,
                "lines": [],
            }
        )
        self.assertEqual(r.status_code, 422)
        body = r.json()
        detail = body.get("detail") or body.get("error", {}).get("details") or body
        if isinstance(detail, dict):
            self.assertIn(detail.get("code"), {"customer_required", "lines_required"})

    def test_api_rejects_missing_lines(self):
        r = self._post(
            {
                "doc_type": "facture",
                "customer_name": "Client SA",
                "amount_ht": 100,
                "lines": [],
            }
        )
        self.assertEqual(r.status_code, 422)
        detail = r.json().get("detail", {})
        self.assertEqual(detail.get("code"), "lines_required")

    def test_api_rejects_invalid_quantity(self):
        r = self._post(
            {
                "doc_type": "facture",
                "customer_name": "Client SA",
                "amount_ht": 100,
                "lines": [_valid_line(quantity=0)],
            }
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["detail"]["code"], "invalid_line_quantity")

    def test_api_accepts_valid_invoice(self):
        r = self._post(
            {
                "doc_type": "facture",
                "customer_name": "Client SA",
                "amount_ht": 100,
                "vat_rate": 20,
                "lines": [_valid_line()],
            }
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["doc_type"], "facture")
        self.assertEqual(body["status"], "draft")
        self.assertEqual(body["amount_ht"], 100)

    def test_api_accepts_valid_quote(self):
        r = self._post(
            {
                "doc_type": "devis",
                "customer_name": "Prospect",
                "amount_ht": 50,
                "lines": [_valid_line(label="Audit", unit_price=50)],
            }
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["doc_type"], "devis")

    def test_api_accepts_zero_ht_free_line_draft(self):
        r = self._post(
            {
                "doc_type": "facture",
                "customer_name": "Client SA",
                "amount_ht": 0,
                "lines": [_valid_line(unit_price=0)],
            }
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["amount_ht"], 0)

    def test_api_accepts_customer_id_without_name(self):
        r = self._post(
            {
                "doc_type": "facture",
                "customer_name": "",
                "customer_id": self.customer.id,
                "amount_ht": 120,
                "lines": [_valid_line(unit_price=120)],
            }
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["customer_name"], "Client CRM")

    def test_patch_rejects_clearing_lines(self):
        doc = create_sales_document(
            self.db,
            organization_id=1,
            doc_type="facture",
            customer_name="Client SA",
            amount_ht=100,
            lines=[_valid_line()],
        )
        r = self.client.patch(
            f"/api/billing/documents/{doc.id}",
            headers=self.headers,
            json={"lines": []},
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["detail"]["code"], "lines_required")
        still = self.db.get(SalesDocument, doc.id)
        self.assertIsNotNone(still)
        self.assertEqual(still.amount_ht, 100)


if __name__ == "__main__":
    unittest.main()
