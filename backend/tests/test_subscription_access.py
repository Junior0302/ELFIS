from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models_saas import Organization, Subscription
from app.subscriptions.access import get_subscription_access


class SubscriptionAccessTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.db.add(Organization(id=1, name="Test SAS"))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_none_has_no_access(self):
        access = get_subscription_access(self.db, 1)
        self.assertEqual(access.subscription_status, "none")
        self.assertFalse(access.has_access)

    def test_cancel_scheduled_keeps_access(self):
        end = datetime.utcnow() + timedelta(days=5)
        self.db.add(
            Subscription(
                organization_id=1,
                plan="pro",
                status="active",
                price=19,
                cancel_at_period_end=True,
                current_period_end=end,
            )
        )
        self.db.commit()
        access = get_subscription_access(self.db, 1)
        self.assertEqual(access.subscription_status, "cancel_scheduled")
        self.assertTrue(access.has_access)

    def test_admin_revoked_blocks(self):
        self.db.add(
            Subscription(
                organization_id=1,
                plan="pro",
                status="active",
                price=19,
                admin_revoked_at=datetime.utcnow(),
                admin_revoked_reason_public="Fraude",
            )
        )
        self.db.commit()
        access = get_subscription_access(self.db, 1)
        self.assertEqual(access.subscription_status, "admin_revoked")
        self.assertFalse(access.has_access)

    def test_past_due_grace_read_only(self):
        self.db.add(
            Subscription(
                organization_id=1,
                plan="pro",
                status="past_due",
                price=19,
                past_due_since=datetime.utcnow(),
            )
        )
        self.db.commit()
        access = get_subscription_access(self.db, 1)
        self.assertEqual(access.subscription_status, "past_due")
        self.assertTrue(access.has_access)
        self.assertTrue(access.read_only)


if __name__ == "__main__":
    unittest.main()
