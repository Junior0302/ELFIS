# ELFIS Permission Engine — RC2.2

## Architecture

Le Permission Engine (`app/iam/`) centralise les décisions d’autorisation plateforme
sans remplacer le RBAC produit tenant (`AuthContext` + `roles.permissions`).

```
Bearer JWT {sub, org_id}
        │
        ├─ get_auth_context          → RBAC organisation (inchangé)
        ├─ require_platform_admin    → gate binaire historique (inchangé)
        └─ get_permission_context    → PermissionContext (IAM RC2.2)
                 │
                 ├─ PermissionResolver  (IAM persisté + compatibilité + org)
                 └─ PermissionService   (has/require)
```

Sources de vérité (étape 2) :

- rôles IAM persistants (`elfis_platform_user_roles`)
- `User.is_platform_admin` / allowlist `PLATFORM_ADMIN_EMAILS` (compatibilité)
- rôle membership org (`owner`, `admin`, …) → permissions org seulement

Voir aussi : [iam-platform-roles.md](./iam-platform-roles.md)

Le frontend **ne fournit jamais** les permissions ; elles sont toujours résolues serveur.
Les permissions **ne sont pas** dans le JWT.

## Catalogue

Format strict : `resource.action` (enum `Permission` dans `permission_catalog.py`).

Domaines inclus : System Health, Jobs/Events, Plateforme, Users, Organizations,
Subscriptions/Billing, Support, Security, Vault, Products.

Toute permission hors catalogue est refusée (`UnknownPermissionError` → HTTP 403 générique).

## Resolver et mapping

| Profil IAM | Attribution étape 1 | Permissions |
|------------|---------------------|-------------|
| `super_admin` | **Jamais automatique** (`force_platform_role` uniquement) | Toutes les permissions du catalogue |
| `platform_admin` | `is_platform_admin` **ou** email allowlist | Ensemble explicite `PLATFORM_ADMIN_PERMISSIONS` (inclut System Health ; **sans** `billing.refund`, `vault.secrets.*`, `support.sessions.impersonate`, `security.permissions.manage`) |
| `platform_operator` | Préparé, non attribué auto | Ops lecture + retry limité |
| `platform_support` | Préparé, non attribué auto | Support lecture |
| `organization_admin` | Alias `owner` / `admin` | Perms org (pas plateforme) |
| `organization_manager` | Alias `cfo` | Lecture org/billing |
| `organization_member` | Alias `comptable` / `employe` | Lecture limitée |
| `viewer` | Alias `auditeur` | Lecture minimale |
| inconnu | — | Aucune permission |

## Règles HTTP

| Situation | Code | Detail |
|-----------|------|--------|
| Non authentifié | **401** | `{code: authentication_required}` |
| Authentifié sans permission | **403** | `{code: permission_denied, message: Accès refusé}` |
| Permission inconnue demandée | **403** | même message générique (pas de fuite catalogue) |

Les refus sont journalisés (`iam_permission_denied`) avec `user_id`, permission, route,
méthode, `organization_id`, `correlation_id` — sans JWT ni secrets.

## Super admin

- Comportement : reçoit **toutes** les permissions connues du catalogue (y compris futures).
- Aucun compte créé automatiquement.
- Aucun email en dur.
- Activation uniquement via `force_platform_role="super_admin"` (tests / future étape).

## Exemple FastAPI

```python
from fastapi import Depends
from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import require_permission

@router.get("/health")
def health(
    ctx: PermissionContext = Depends(require_permission(Permission.SYSTEM_HEALTH_READ.value)),
):
    ...
```

Compatibilité : `require_platform_admin` continue d’exister et n’est pas modifié.

## Routes migrées (étape 1)

| Route | Permission |
|-------|------------|
| `GET /api/admin/system/health` | `system.health.read` |
| `GET /api/admin/system/metrics` | `system.metrics.read` |
| `GET /api/admin/system/alerts` | `system.alerts.read` |
| `GET /api/admin/system/logs` | `system.logs.read` |

Les platform admins actuels conservent l’accès via le mapping `platform_admin`.

## Limites actuelles

- Permissions absentes du JWT (rechargées à chaque requête + cache TTL court).
- RBAC produit (`AuthContext.require`) et IAM plateforme coexistent.
- Frontend : pas d’UI complète de gestion des rôles.
- `require_platform_admin` et `PLATFORM_ADMIN_EMAILS` conservés (compatibilité).

## Plan de migration des routes

1. ✅ System Health
2. ✅ Persistance rôles plateforme (étape 2)
3. Jobs / Events admin
4. Dashboard / organisations / users platform
5. Raffinement + retrait progressif allowlist

## Rappel

Les permissions de cette étape sont **dérivées des rôles existants**.
Masquer un menu frontend ne remplace jamais une autorisation serveur.
