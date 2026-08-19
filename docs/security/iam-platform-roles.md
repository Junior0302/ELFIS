# Rôles plateforme IAM persistants — RC2.2 étape 2

## Tables

| Table | Rôle |
|-------|------|
| `elfis_platform_roles` | Rôles plateforme (système + custom) |
| `elfis_platform_permissions` | Catalogue persisté (codes = `permission_catalog`) |
| `elfis_platform_role_permissions` | M2M rôle ↔ permission |
| `elfis_platform_user_roles` | Attribution utilisateur ↔ rôle |

Distinct du RBAC organisation : tables SaaS `roles` / `permissions` / `organization_members`.

Migration : `backend/sql/elfis_iam_platform_postgres.sql` (IF NOT EXISTS), enregistrée dans
`scripts/rc1/migrate_sql.py` et `scripts/production/check_migrations.py`.
**Alembic n’est pas utilisé** (convention RC1).

## Rôles système

| Code | Permissions |
|------|-------------|
| `super_admin` | Toutes les permissions du catalogue |
| `platform_admin` | Admin générale (System Health, users, orgs, billing sans refund, IAM manage…) |
| `platform_operator` | Health, jobs, events, logs, incidents |
| `platform_support` | Support lecture limitée |
| `platform_viewer` | Dashboard + health/metrics/alerts lecture |

Aucun utilisateur créé. Aucune attribution automatique.

## Resolver hybride

1. Rôles IAM actifs non expirés  
2. Compatibilité `is_platform_admin` / `PLATFORM_ADMIN_EMAILS` → ensemble `platform_admin`  
3. Rôles org (jamais de permissions plateforme)  
4. Fusion  

## Commandes

```bash
python -m scripts.iam.sync_permissions
python -m scripts.iam.sync_permissions --bootstrap-roles
python -m scripts.iam.assign_platform_role --user-id ID --role platform_viewer --confirm
python -m scripts.iam.assign_platform_role --user-id ID --role super_admin --confirm
python -m scripts.iam.assign_platform_role --user-id ID --role super_admin --revoke --confirm
```

## API minimale

- `GET /api/admin/iam/roles` — `security.permissions.read|manage`
- `GET /api/admin/iam/roles/{id}`
- `GET /api/admin/iam/users/{id}/roles`
- `GET /api/admin/iam/users/{id}/permissions`
- `POST /api/admin/iam/users/{id}/roles/{role_id}` — `security.permissions.manage`
- `DELETE /api/admin/iam/users/{id}/roles/{role_id}` — `security.permissions.manage`

## Retrait futur de PLATFORM_ADMIN_EMAILS

1. Attribuer `platform_admin` IAM aux opérateurs concernés  
2. Vérifier accès System Health / dashboard  
3. Désactiver allowlist en config staging  
4. Retirer le chemin de compatibilité dans une étape ultérieure  

## Procédure de secours

Si mauvaise attribution `super_admin` :

```bash
python -m scripts.iam.assign_platform_role --user-id ID --role super_admin --revoke --confirm
```

Vérifier ensuite `GET /api/admin/iam/users/{id}/roles`.

## Limites

- Pas d’UI frontend complète  
- Permissions absentes du JWT  
- `require_platform_admin` toujours présent  
- Cache TTL 30 s (invalidé à assign/revoke)  
