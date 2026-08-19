-- ELFIS IAM Platform Roles V1 (Postgres)
-- Tables nouvelles uniquement. Ne touche pas au RBAC org (roles / permissions SaaS).

CREATE TABLE IF NOT EXISTS elfis_platform_roles (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_user_id INTEGER REFERENCES users(id),
    CONSTRAINT uq_elfis_platform_roles_code UNIQUE (code)
);

CREATE INDEX IF NOT EXISTS ix_elfis_platform_roles_active
    ON elfis_platform_roles (is_active);
CREATE INDEX IF NOT EXISTS ix_elfis_platform_roles_system
    ON elfis_platform_roles (is_system);

CREATE TABLE IF NOT EXISTS elfis_platform_permissions (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(128) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_platform_permissions_code UNIQUE (code)
);

CREATE INDEX IF NOT EXISTS ix_elfis_platform_permissions_resource
    ON elfis_platform_permissions (resource);
CREATE INDEX IF NOT EXISTS ix_elfis_platform_permissions_active
    ON elfis_platform_permissions (is_active);

CREATE TABLE IF NOT EXISTS elfis_platform_role_permissions (
    id VARCHAR(36) PRIMARY KEY,
    role_id VARCHAR(36) NOT NULL REFERENCES elfis_platform_roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(36) NOT NULL REFERENCES elfis_platform_permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_user_id INTEGER REFERENCES users(id),
    CONSTRAINT uq_elfis_platform_role_perm UNIQUE (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS ix_elfis_platform_role_perm_role
    ON elfis_platform_role_permissions (role_id);
CREATE INDEX IF NOT EXISTS ix_elfis_platform_role_perm_perm
    ON elfis_platform_role_permissions (permission_id);

CREATE TABLE IF NOT EXISTS elfis_platform_user_roles (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    role_id VARCHAR(36) NOT NULL REFERENCES elfis_platform_roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    assigned_by_user_id INTEGER REFERENCES users(id),
    expires_at TIMESTAMP WITHOUT TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_elfis_platform_user_role UNIQUE (user_id, role_id),
    CONSTRAINT ck_elfis_platform_user_role_expires CHECK (
        expires_at IS NULL OR expires_at > assigned_at
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_platform_user_roles_user
    ON elfis_platform_user_roles (user_id);
CREATE INDEX IF NOT EXISTS ix_elfis_platform_user_roles_role
    ON elfis_platform_user_roles (role_id);
CREATE INDEX IF NOT EXISTS ix_elfis_platform_user_roles_active
    ON elfis_platform_user_roles (is_active);
