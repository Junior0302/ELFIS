"""Repositories IAM plateforme."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session

from app.iam.iam_models import (
    ElfisPlatformPermission,
    ElfisPlatformRole,
    ElfisPlatformRolePermission,
    ElfisPlatformUserRole,
)


def _utcnow() -> datetime:
    return datetime.utcnow()


class PlatformRoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, role_id: str) -> ElfisPlatformRole | None:
        return self._db.get(ElfisPlatformRole, role_id)

    def get_by_code(self, code: str) -> ElfisPlatformRole | None:
        return (
            self._db.query(ElfisPlatformRole)
            .filter(ElfisPlatformRole.code == code)
            .one_or_none()
        )

    def list_roles(self, *, active_only: bool = False) -> list[ElfisPlatformRole]:
        q = self._db.query(ElfisPlatformRole).order_by(ElfisPlatformRole.code)
        if active_only:
            q = q.filter(ElfisPlatformRole.is_active.is_(True))
        return list(q.all())

    def create(
        self,
        *,
        code: str,
        name: str,
        description: str | None = None,
        is_system: bool = False,
        is_active: bool = True,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> ElfisPlatformRole:
        row = ElfisPlatformRole(
            code=code,
            name=name,
            description=description,
            is_system=is_system,
            is_active=is_active,
            created_by_user_id=created_by_user_id,
        )
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save(self, row: ElfisPlatformRole, *, commit: bool = True) -> ElfisPlatformRole:
        row.updated_at = _utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row


class PlatformPermissionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_code(self, code: str) -> ElfisPlatformPermission | None:
        return (
            self._db.query(ElfisPlatformPermission)
            .filter(ElfisPlatformPermission.code == code)
            .one_or_none()
        )

    def list_all(self) -> list[ElfisPlatformPermission]:
        return list(
            self._db.query(ElfisPlatformPermission)
            .order_by(ElfisPlatformPermission.code)
            .all()
        )

    def upsert(
        self,
        *,
        code: str,
        resource: str,
        action: str,
        description: str | None,
        is_active: bool = True,
        commit: bool = True,
    ) -> ElfisPlatformPermission:
        row = self.get_by_code(code)
        if row is None:
            row = ElfisPlatformPermission(
                code=code,
                resource=resource,
                action=action,
                description=description,
                is_active=is_active,
            )
            self._db.add(row)
        else:
            row.resource = resource
            row.action = action
            row.description = description
            row.is_active = is_active
            row.updated_at = _utcnow()
            self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row


class PlatformUserRoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_assignment(self, user_id: int, role_id: str) -> ElfisPlatformUserRole | None:
        return (
            self._db.query(ElfisPlatformUserRole)
            .filter(
                ElfisPlatformUserRole.user_id == user_id,
                ElfisPlatformUserRole.role_id == role_id,
            )
            .one_or_none()
        )

    def list_for_user(
        self, user_id: int, *, active_only: bool = True, now: datetime | None = None
    ) -> list[ElfisPlatformUserRole]:
        now = now or _utcnow()
        q = self._db.query(ElfisPlatformUserRole).filter(
            ElfisPlatformUserRole.user_id == user_id
        )
        if active_only:
            q = q.filter(ElfisPlatformUserRole.is_active.is_(True))
            q = q.filter(
                (ElfisPlatformUserRole.expires_at.is_(None))
                | (ElfisPlatformUserRole.expires_at > now)
            )
        return list(q.all())

    def list_active_roles_with_codes(
        self, user_id: int, *, now: datetime | None = None
    ) -> list[tuple[ElfisPlatformUserRole, ElfisPlatformRole]]:
        now = now or _utcnow()
        rows = (
            self._db.query(ElfisPlatformUserRole, ElfisPlatformRole)
            .join(
                ElfisPlatformRole,
                ElfisPlatformRole.id == ElfisPlatformUserRole.role_id,
            )
            .filter(
                ElfisPlatformUserRole.user_id == user_id,
                ElfisPlatformUserRole.is_active.is_(True),
                ElfisPlatformRole.is_active.is_(True),
                (ElfisPlatformUserRole.expires_at.is_(None))
                | (ElfisPlatformUserRole.expires_at > now),
            )
            .all()
        )
        return list(rows)

    def assign(
        self,
        *,
        user_id: int,
        role_id: str,
        assigned_by_user_id: int | None = None,
        expires_at: datetime | None = None,
        commit: bool = True,
    ) -> ElfisPlatformUserRole:
        existing = self.get_assignment(user_id, role_id)
        if existing:
            existing.is_active = True
            existing.assigned_at = _utcnow()
            existing.assigned_by_user_id = assigned_by_user_id
            existing.expires_at = expires_at
            self._db.add(existing)
            row = existing
        else:
            row = ElfisPlatformUserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by_user_id=assigned_by_user_id,
                expires_at=expires_at,
                is_active=True,
            )
            self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def revoke(self, user_id: int, role_id: str, *, commit: bool = True) -> bool:
        existing = self.get_assignment(user_id, role_id)
        if not existing or not existing.is_active:
            return False
        existing.is_active = False
        self._db.add(existing)
        if commit:
            self._db.commit()
        else:
            self._db.flush()
        return True


class PlatformRolePermissionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_permission_codes_for_role(self, role_id: str) -> list[str]:
        rows = (
            self._db.query(ElfisPlatformPermission.code)
            .join(
                ElfisPlatformRolePermission,
                ElfisPlatformRolePermission.permission_id == ElfisPlatformPermission.id,
            )
            .filter(
                ElfisPlatformRolePermission.role_id == role_id,
                ElfisPlatformPermission.is_active.is_(True),
            )
            .all()
        )
        return [r[0] for r in rows]

    def set_permissions(
        self,
        role_id: str,
        permission_ids: Sequence[str],
        *,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> None:
        existing = (
            self._db.query(ElfisPlatformRolePermission)
            .filter(ElfisPlatformRolePermission.role_id == role_id)
            .all()
        )
        by_perm = {e.permission_id: e for e in existing}
        wanted = set(permission_ids)
        for pid, row in list(by_perm.items()):
            if pid not in wanted:
                self._db.delete(row)
        for pid in wanted:
            if pid not in by_perm:
                self._db.add(
                    ElfisPlatformRolePermission(
                        role_id=role_id,
                        permission_id=pid,
                        created_by_user_id=created_by_user_id,
                    )
                )
        if commit:
            self._db.commit()
        else:
            self._db.flush()

    def grant(
        self,
        role_id: str,
        permission_id: str,
        *,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> ElfisPlatformRolePermission:
        row = (
            self._db.query(ElfisPlatformRolePermission)
            .filter(
                ElfisPlatformRolePermission.role_id == role_id,
                ElfisPlatformRolePermission.permission_id == permission_id,
            )
            .one_or_none()
        )
        if row is None:
            row = ElfisPlatformRolePermission(
                role_id=role_id,
                permission_id=permission_id,
                created_by_user_id=created_by_user_id,
            )
            self._db.add(row)
            if commit:
                self._db.commit()
                self._db.refresh(row)
            else:
                self._db.flush()
        return row

    def revoke(self, role_id: str, permission_id: str, *, commit: bool = True) -> bool:
        row = (
            self._db.query(ElfisPlatformRolePermission)
            .filter(
                ElfisPlatformRolePermission.role_id == role_id,
                ElfisPlatformRolePermission.permission_id == permission_id,
            )
            .one_or_none()
        )
        if row is None:
            return False
        self._db.delete(row)
        if commit:
            self._db.commit()
        else:
            self._db.flush()
        return True
