"""Tests sync catalogue."""

from __future__ import annotations

import pytest

from app.iam.permission_catalog import all_permissions
from app.iam.permission_sync import sync_permissions_from_catalog
from app.iam.platform_role_repository import PlatformPermissionRepository
from tests.iam.conftest_helpers import make_iam_db


def test_sync_idempotent_creates_catalog():
    factory, _ = make_iam_db()
    db = factory()
    a = sync_permissions_from_catalog(db, commit=True)
    b = sync_permissions_from_catalog(db, commit=True)
    assert a["created"] == len(all_permissions())
    assert b["created"] == 0
    assert b["unchanged"] + b["updated"] == len(all_permissions())
    repo = PlatformPermissionRepository(db)
    assert len(repo.list_all()) == len(all_permissions())
    db.close()


def test_unknown_permission_not_in_catalog():
    from app.iam.permission_catalog import is_known_permission

    assert not is_known_permission("totally.fake.permission")


def test_mark_missing_inactive():
    from app.iam.iam_models import ElfisPlatformPermission

    factory, _ = make_iam_db()
    db = factory()
    sync_permissions_from_catalog(db, commit=True)
    db.add(
        ElfisPlatformPermission(
            code="legacy.obsolete.perm",
            resource="legacy",
            action="obsolete.perm",
            is_active=True,
        )
    )
    db.commit()
    stats = sync_permissions_from_catalog(db, mark_missing_inactive=True, commit=True)
    assert stats["inactivated"] >= 1
    row = (
        db.query(ElfisPlatformPermission)
        .filter(ElfisPlatformPermission.code == "legacy.obsolete.perm")
        .one()
    )
    assert row.is_active is False
    # Pas de suppression
    assert db.query(ElfisPlatformPermission).count() >= len(all_permissions()) + 1
    db.close()
