# 05 — Modèle permissions par espace (cible)

## Architecture cible

```
Organisation
├── rôle global (owner | admin | manager | member | viewer)
├── espaces accessibles
└── permissions métier par espace
```

```ts
type ElfisMembership = {
  globalRole: 'owner' | 'admin' | 'manager' | 'member' | 'viewer'
  spaces: {
    finance?: SpacePermission
    commercial?: SpacePermission
    documents?: SpacePermission
    hr?: SpacePermission
  }
}
```

## État actuel (audit)

- RBAC org : rôle unique + liste de permissions plates
- Pas de colonne « accès espaces » exposée à l’UI membres
- IAM `OrganizationRole` mappe déjà cfo→manager, comptable→member, etc.

## Feature flag

`VITE_ELFIS_SPACE_PERMISSIONS=true` → colonne « Accès aux espaces » dans la table membres.  
Par défaut **désactivée** — aucune donnée inventée.

Ne pas migrer les tables sans audit dédié.
