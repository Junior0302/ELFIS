from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Organization, OrganizationMember, Subscription, User
from app.routers import auth as auth_router
from app.routers import org as org_router
from app.services.auth import create_access_token, ensure_rbac_catalog
from app.services.invitations import (
    accept_invitation,
    create_invitation,
    get_invitation_by_token,
    leave_organization,
    refuse_invitation,
)
from app.services.plan_features import can_invite_more, can_use_feature, org_effective_plan


class TeamInvitationsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db = self.session_factory()
        roles = ensure_rbac_catalog(self.db)

        self.org = Organization(name="Cabinet Pro", subscription_plan="pro")
        self.db.add(self.org)
        self.db.flush()
        self.db.add(
            Subscription(
                organization_id=self.org.id,
                plan="pro",
                status="active",
                price=19.0,
                stripe_customer_id="cus_team",
                stripe_subscription_id="sub_team",
            )
        )

        self.owner = User(
            first_name="Owner",
            last_name="One",
            email="owner@team.test",
            password_hash="",
            firebase_uid="fb_owner",
            status="active",
        )
        self.member = User(
            first_name="Alice",
            last_name="Collab",
            email="alice@team.test",
            password_hash="",
            firebase_uid="fb_alice",
            status="active",
        )
        self.outsider = User(
            first_name="Bob",
            last_name="Other",
            email="bob@other.test",
            password_hash="",
            firebase_uid="fb_bob",
            status="active",
        )
        self.db.add_all([self.owner, self.member, self.outsider])
        self.db.flush()

        self.other_org = Organization(name="Autre SAS", subscription_plan="starter")
        self.db.add(self.other_org)
        self.db.flush()

        self.db.add_all(
            [
                OrganizationMember(
                    user_id=self.owner.id,
                    organization_id=self.org.id,
                    role_id=roles["owner"].id,
                    status="active",
                ),
                OrganizationMember(
                    user_id=self.member.id,
                    organization_id=self.other_org.id,
                    role_id=roles["owner"].id,
                    status="active",
                ),
                OrganizationMember(
                    user_id=self.outsider.id,
                    organization_id=self.other_org.id,
                    role_id=roles["owner"].id,
                    status="active",
                ),
            ]
        )
        self.db.commit()

        app = FastAPI()
        app.include_router(auth_router.router, prefix="/api")
        app.include_router(org_router.router, prefix="/api")

        def override_db():
            try:
                yield self.db
            finally:
                pass

        self._auth_user = self.owner
        self._auth_org = self.org.id
        self._auth_role = "owner"
        self._auth_perms = ["*"]

        def override_auth():
            return AuthContext(
                self._auth_user,
                self._auth_org,
                self._auth_role,
                self._auth_perms,
            )

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_auth_context] = override_auth
        app.dependency_overrides[require_active_subscription] = override_auth
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _as(self, user: User, org_id: int, role: str, perms: list[str]):
        self._auth_user = user
        self._auth_org = org_id
        self._auth_role = role
        self._auth_perms = perms

    def test_owner_invites_existing_user_and_member_accepts(self):
        invite, raw, _ = create_invitation(
            self.db,
            organization_id=self.org.id,
            email=self.member.email,
            role="comptable",
            invited_by=self.owner.id,
        )
        self.assertEqual(invite.status, "pending")

        self._as(self.member, self.other_org.id, "owner", ["*"])
        listed = self.client.get("/api/auth/invitations")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["invitations"]), 1)

        accepted = self.client.post(
            "/api/auth/invitations/accept",
            json={"token": raw},
        )
        self.assertEqual(accepted.status_code, 200)
        body = accepted.json()
        self.assertEqual(body["organization_id"], self.org.id)
        org_ids = {m["organization_id"] for m in body["memberships"]}
        self.assertIn(self.org.id, org_ids)
        self.assertEqual(len(body["pending_invitations"]), 0)

        # Abonnement hérité de l'org (pas d'abo personnel requis)
        plan, status = org_effective_plan(self.db, self.org.id)
        self.assertEqual(plan, "pro")
        self.assertEqual(status, "active")
        member_row = next(m for m in body["memberships"] if m["organization_id"] == self.org.id)
        self.assertEqual(member_row["plan"], "pro")
        self.assertIsNone(
            self.db.query(Subscription)
            .filter(Subscription.organization_id == self.other_org.id, Subscription.status == "active")
            .first()
        )

    def test_token_cannot_be_reused_and_expired_rejected(self):
        invite, raw, _ = create_invitation(
            self.db,
            organization_id=self.org.id,
            email=self.member.email,
            role="employe",
            invited_by=self.owner.id,
        )
        accept_invitation(self.db, user=self.member, token=raw)
        with self.assertRaises(ValueError):
            accept_invitation(self.db, user=self.member, token=raw)

        invite2, raw2, _ = create_invitation(
            self.db,
            organization_id=self.org.id,
            email=self.outsider.email,
            role="auditeur",
            invited_by=self.owner.id,
        )
        invite2.expires_at = datetime.utcnow() - timedelta(days=1)
        self.db.add(invite2)
        self.db.commit()
        expired = get_invitation_by_token(self.db, raw2)
        self.assertEqual(expired.status, "expired")
        with self.assertRaises(ValueError):
            accept_invitation(self.db, user=self.outsider, token=raw2)

    def test_viewer_cannot_modify_and_permission_vs_plan(self):
        ok, reason = can_use_feature(
            member_status="active",
            permissions=["invoice.read", "documents.read"],
            plan="business",
            subscription_status="active",
            feature="document_analysis",
            permission="invoice.delete",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "permission_denied")

        ok2, reason2 = can_use_feature(
            member_status="active",
            permissions=["*"],
            plan="starter",
            subscription_status="none",
            feature="intelligence_dashboard",
            permission=None,
        )
        self.assertFalse(ok2)
        self.assertIn(reason2, {"plan_missing_feature", "subscription_inactive"})

        ok2b, reason2b = can_use_feature(
            member_status="active",
            permissions=["*"],
            plan="starter",
            subscription_status="active",
            feature="intelligence_dashboard",
            permission=None,
        )
        # starter actif sans feature → plan ; pro/business l'incluent
        self.assertTrue(ok2b or reason2b == "plan_missing_feature")

        ok3, reason3 = can_use_feature(
            member_status="active",
            permissions=["ai.analysis"],
            plan="pro",
            subscription_status="active",
            feature="advanced_analysis",
            permission="ai.analysis",
        )
        self.assertTrue(ok3)
        self.assertEqual(reason3, "ok")

    def test_removed_member_loses_access_and_isolation(self):
        invite, raw, _ = create_invitation(
            self.db,
            organization_id=self.org.id,
            email=self.member.email,
            role="employe",
            invited_by=self.owner.id,
        )
        accept_invitation(self.db, user=self.member, token=raw)

        self._as(self.owner, self.org.id, "owner", ["*"])
        members = self.client.get(f"/api/org/{self.org.id}/members")
        membership_id = next(
            m["membership_id"]
            for m in members.json()["members"]
            if m["user_id"] == self.member.id
        )
        removed = self.client.delete(f"/api/org/{self.org.id}/members/{membership_id}")
        self.assertEqual(removed.status_code, 200)

        from app.services.auth import get_user_memberships

        member_orgs = {
            m["organization_id"] for m in get_user_memberships(self.db, self.member.id)
        }
        self.assertNotIn(self.org.id, member_orgs)

        # Isolation : outsider ne voit pas l'org Pro
        outsider_orgs = {
            m["organization_id"] for m in get_user_memberships(self.db, self.outsider.id)
        }
        self.assertNotIn(self.org.id, outsider_orgs)

        # Départ volontaire d'un non-owner
        roles = ensure_rbac_catalog(self.db)
        collab = OrganizationMember(
            user_id=self.outsider.id,
            organization_id=self.org.id,
            role_id=roles["employe"].id,
            status="active",
        )
        self.db.add(collab)
        self.db.commit()
        leave_organization(self.db, user=self.outsider, organization_id=self.org.id)
        outsider_orgs2 = {
            m["organization_id"] for m in get_user_memberships(self.db, self.outsider.id)
        }
        self.assertNotIn(self.org.id, outsider_orgs2)

    def test_member_cannot_self_promote_admin_cannot_remove_owner(self):
        roles = ensure_rbac_catalog(self.db)
        membership = OrganizationMember(
            user_id=self.member.id,
            organization_id=self.org.id,
            role_id=roles["admin"].id,
            status="active",
        )
        self.db.add(membership)
        self.db.commit()

        self._as(self.member, self.org.id, "admin", ["users.manage"])
        owner_membership = (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == self.owner.id,
                OrganizationMember.organization_id == self.org.id,
            )
            .first()
        )
        bad = self.client.delete(f"/api/org/{self.org.id}/members/{owner_membership.id}")
        self.assertEqual(bad.status_code, 400)

        self_update = self.client.patch(
            f"/api/org/{self.org.id}/members/{membership.id}",
            json={"role": "owner"},
        )
        self.assertEqual(self_update.status_code, 400)

    def test_seat_limit_and_stripe_org_scoped(self):
        # Starter sans abo : 1 siège
        starter = Organization(name="Solo", subscription_plan="starter")
        self.db.add(starter)
        self.db.flush()
        roles = ensure_rbac_catalog(self.db)
        self.db.add(
            OrganizationMember(
                user_id=self.outsider.id,
                organization_id=starter.id,
                role_id=roles["owner"].id,
                status="active",
            )
        )
        self.db.commit()
        ok, msg = can_invite_more(self.db, starter.id)
        self.assertFalse(ok)
        self.assertTrue("1 membre" in msg or "Pro" in msg or "offre supérieure" in msg)

        ok_pro, _ = can_invite_more(self.db, self.org.id)
        self.assertTrue(ok_pro)

        # Stripe reste rattaché à l'organisation
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.organization_id == self.org.id)
            .first()
        )
        self.assertEqual(sub.stripe_subscription_id, "sub_team")
        self.assertIsNone(
            self.db.query(Subscription)
            .filter(Subscription.organization_id == self.other_org.id)
            .first()
        )

    def test_refuse_invitation(self):
        _, raw, _ = create_invitation(
            self.db,
            organization_id=self.org.id,
            email=self.member.email,
            role="cfo",
            invited_by=self.owner.id,
        )
        refuse_invitation(self.db, user=self.member, token=raw)
        with self.assertRaises(ValueError):
            accept_invitation(self.db, user=self.member, token=raw)

    def test_jwt_token_helper_still_works(self):
        token = create_access_token({"sub": str(self.owner.id), "org_id": self.org.id})
        self.assertTrue(token)


if __name__ == "__main__":
    unittest.main()
