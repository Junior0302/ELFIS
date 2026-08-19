"""Modèles SQLAlchemy — IAM plateforme (elfis_platform_*).

Distinct du RBAC organisation (tables roles / permissions SaaS).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisPlatformRole(Base):
    __tablename__ = "elfis_platform_roles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_elfis_platform_roles_code"),
        Index("ix_elfis_platform_roles_active", "is_active"),
        Index("ix_elfis_platform_roles_system", "is_system"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class ElfisPlatformPermission(Base):
    __tablename__ = "elfis_platform_permissions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_elfis_platform_permissions_code"),
        Index("ix_elfis_platform_permissions_resource", "resource"),
        Index("ix_elfis_platform_permissions_active", "is_active"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    code = Column(String(128), nullable=False)
    resource = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisPlatformRolePermission(Base):
    __tablename__ = "elfis_platform_role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_elfis_platform_role_perm"),
        Index("ix_elfis_platform_role_perm_role", "role_id"),
        Index("ix_elfis_platform_role_perm_perm", "permission_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    role_id = Column(
        String(36),
        ForeignKey("elfis_platform_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id = Column(
        String(36),
        ForeignKey("elfis_platform_permissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class ElfisPlatformUserRole(Base):
    __tablename__ = "elfis_platform_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_elfis_platform_user_role"),
        Index("ix_elfis_platform_user_roles_user", "user_id"),
        Index("ix_elfis_platform_user_roles_role", "role_id"),
        Index("ix_elfis_platform_user_roles_active", "is_active"),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > assigned_at",
            name="ck_elfis_platform_user_role_expires",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(
        String(36),
        ForeignKey("elfis_platform_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
