"""Tests cache permissions IAM."""

from __future__ import annotations

from app.iam import permission_cache as perm_cache
from app.iam.permission_cache import configure_permission_cache
from app.iam.platform_role_service import PlatformRoleService
from app.iam.system_roles import bootstrap_system_roles
from tests.iam.conftest_helpers import make_iam_db, seed_user


def setup_function():
    configure_permission_cache(ttl_seconds=60.0)
    perm_cache.effective_permissions_cache.clear()


def teardown_function():
    perm_cache.effective_permissions_cache.clear()


def test_cache_hit_and_invalidate_on_assign_revoke():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    svc = PlatformRoleService(db)

    svc.assign_role_to_user(user.id, "platform_viewer")
    p1 = svc.effective_permissions_for_user(user.id)
    p2 = svc.effective_permissions_for_user(user.id)
    assert p1 == p2
    assert perm_cache.effective_permissions_cache.get(f"user:{user.id}") == p1

    svc.assign_role_to_user(user.id, "platform_operator")
    assert perm_cache.effective_permissions_cache.get(f"user:{user.id}") is None
    p3 = svc.effective_permissions_for_user(user.id)
    assert "jobs.read" in p3

    svc.revoke_role_from_user(user.id, "platform_operator")
    assert perm_cache.effective_permissions_cache.get(f"user:{user.id}") is None
    db.close()


def test_cache_disabled():
    configure_permission_cache(ttl_seconds=0)
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    svc = PlatformRoleService(db)
    svc.assign_role_to_user(user.id, "platform_viewer")
    svc.effective_permissions_for_user(user.id)
    assert perm_cache.effective_permissions_cache.get(f"user:{user.id}") is None
    db.close()
