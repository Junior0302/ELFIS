"""Tests repository couche basse."""

from __future__ import annotations

from app.iam.platform_role_repository import PlatformRoleRepository
from app.iam.system_roles import bootstrap_system_roles
from tests.iam.conftest_helpers import make_iam_db


def test_role_repository_list_and_get():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    repo = PlatformRoleRepository(db)
    roles = repo.list_roles(active_only=True)
    assert len(roles) >= 5
    admin = repo.get_by_code("platform_admin")
    assert admin is not None
    assert admin.is_system is True
    assert repo.get_by_id(admin.id) is admin or repo.get_by_id(admin.id).code == "platform_admin"
    db.close()
