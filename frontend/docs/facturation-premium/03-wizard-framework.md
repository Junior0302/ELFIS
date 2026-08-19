# 03 — Wizard Framework

## Emplacement

`frontend/src/wizard-framework/` — miroir architectural de `widget-framework/`.

## Composants

| Export | Rôle |
|--------|------|
| `WizardContainer` | Shell layout (header, progress, sidebar, content, footer) |
| `WizardStep` | Contenu d’une étape |
| `WizardSidebar` | Liste navigable des étapes |
| `WizardProgress` | Barre + dots (role=progressbar) |
| `WizardFooter` / `WizardNavigation` / `WizardActions` | Actions bas de parcours |
| `WizardSummary` | Panneau résumé |
| `WizardValidation` | Liste d’issues / empty state |
| `useWizardNavigation` | Hook state machine générique |

## Principes

- Produit-agnostique (Sales / Inventory / HR / Project)
- Tokens `--ps-*` / Design System ELFIS
- Accessibilité : titres, `aria-current="step"`, focus-visible
- `prefers-reduced-motion` respecté

## Consommateur F1.0

Facturation uniquement. Aucune dépendance inverse framework → ComptaPilot.
