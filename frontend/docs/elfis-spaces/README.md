# Hub Espaces ELFIS — BRAND.ELFIS.1

Transformation du launcher « Applications » en **Hub des espaces métier ELFIS**.
Terminologie UX et cartes domaines ; **routes et moteurs inchangés**.

## Statut

| Phase | Scope | Statut |
|-------|--------|--------|
| NAV.CORE.1 | Menu plateforme ELFIS | Livré |
| NAV.DOMAIN.1 | Nav Finance / Commercial | Livré |
| **BRAND.ELFIS.1** | Hub Espaces (launcher) | **Livré — STOP revue** |

## Index

| Doc | Contenu |
|-----|---------|
| [01](./01-current-launcher-audit.md) | Audit launcher AVANT |
| [02](./02-spaces-information-architecture.md) | IA espaces métier |
| [03](./03-space-cards-contract.md) | Contrat cartes communes |
| [04](./04-search-aliases.md) | Recherche + alias |
| [05](./05-continue-resume.md) | Continuer / Reprendre |
| [06](./06-routes-mapping.md) | Mapping routes réelles |
| [07](./07-visual-language.md) | Navy + accents domaines |
| [08](./08-test-plan.md) | EH01–EH30 |
| [09](./09-implementation-report.md) | Rapport GO |

## Module

`frontend/src/app-launcher/`

- `spacesCatalog.ts` — 6 espaces (Finance… Support)
- `spacesModel.ts` — résolution / Continuer / recherche
- `AppLauncher*.tsx` — trigger, panel, overlays

Terminologie UI : **Espaces** / **Espaces ELFIS** (pas « Applications »).
Accueil plateforme : **Accueil ELFIS** (pas « ELFIS Home » dans ce hub).

## Hors scope

- Pas de refonte Home
- Pas de migration pages métier
- Pas de modification moteurs ComptaPilot / SalesPilot / etc.
- Pas de commit (revue manuelle)
