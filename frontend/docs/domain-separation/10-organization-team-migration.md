# 10 — Organization & team migration

## Organisation

- **Cible** : `/platform/organization`
- **Implémentation** : `PlatformOrganizationPage` → réutilise `OrganisationPage`
- **Legacy** : `/organisation` → redirect
- **API** : `api.orgDetail` / update inchangés
- **Factures / PDF** : continuent de lire l’org via API (pas de rupture)

## Membres

- **Cible** : `/platform/members`
- **Implémentation** : `PlatformMembersPage` → `AdminEquipePage`
- **Legacy** : `/admin/equipe`, `/team` → `/platform/members`
- **API** : `orgMembers`, invitations, Firebase sync inchangés

## ComptaPilot

- Ne gère plus la structure membres dans le menu métier
- Liens Paramètres → ELFIS Core
- Peut toujours afficher un auteur / propriétaire document

## Non fait

- Tables non fusionnées
- Pas de page Teams / Roles séparée (redirect members)
