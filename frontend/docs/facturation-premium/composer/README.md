# Document Composer Premium — F1.1

Documentation du chantier **F1.1** (UX création Facture / Devis / Avoir).

| Doc | Contenu |
|-----|---------|
| [01-architecture.md](./01-architecture.md) | Composer framework + intégration |
| [02-layout.md](./02-layout.md) | Grille 20 / 50 / 30 |
| [03-focus-mode.md](./03-focus-mode.md) | Mode focus création |
| [04-preview.md](./04-preview.md) | Aperçu structuré + PDF |
| [05-catalog.md](./05-catalog.md) | Catalogue local / Inventory stub |
| [06-validation.md](./06-validation.md) | Contrôles F1.0 |
| [07-responsive.md](./07-responsive.md) | Breakpoints |
| [08-roadmap.md](./08-roadmap.md) | F1.1 → F1.2 |
| [09-tests.md](./09-tests.md) | CP01–CP40 |
| [10-implementation-report.md](./10-implementation-report.md) | Rapport livrable |

## Routes

| Espace | Path | Composant |
|--------|------|-----------|
| Nouveau document | `/facturation/nouveau` | `FacturationComposerPage` |

Redirects F1.0 conservés (`catalogue` → `/catalogue`, `activite` → `/activites`, `?customer_id=`).

## Code

- Framework : `frontend/src/composer-framework/`
- Page : `frontend/src/pages/facturation/FacturationComposerPage.tsx`
- Workflow (inchangé métier) : `frontend/src/comptapilot/facturation/workflow/`

## Références

- F1.0 : `../` (workflow foundation)
- Blueprint V1 : `../../platform-blueprint/`
