# Identité visuelle ELFIS — BRAND.ELFIS.2

Tokens navy/bleu signature, surfaces plateforme neutres, rôles globaux transverses.
Priorité : `/platform/members`.

## Statut

| Phase | Scope | Statut |
|-------|--------|--------|
| BRAND.ELFIS.1 | Hub Espaces launcher | Livré |
| **BRAND.ELFIS.2** | Identité ELFIS + rôles globaux | **Livré — STOP revue** |

## Index

| Doc | Contenu |
|-----|---------|
| [01](./01-runtime-color-audit.md) | Audit couleurs runtime |
| [02](./02-elfis-color-system.md) | Système de tokens |
| [03](./03-department-accent-rules.md) | Accents métier vs plateforme |
| [04](./04-global-role-model.md) | Rôles globaux UI |
| [05](./05-space-permission-model.md) | Modèle cible espaces |
| [06](./06-members-page.md) | Page Membres et équipes |
| [07](./07-accessibility.md) | Contraste / a11y |
| [08](./08-test-plan.md) | EB01–EB30 |
| [09](./09-implementation-report.md) | Rapport GO |

## Modules

- `frontend/src/design-system/colors/elfisBrandTokens.ts` + `elfis-brand.css`
- `frontend/src/platform-roles/globalRoles.ts`
- `frontend/src/pages/AdminEquipePage.tsx` + `elfis-members.css`

## Hors scope

- Pas de refonte Finance / Commercial
- Pas de migration tables RBAC
- Pas de modification moteurs métier
- Pas de commit (revue manuelle)
