# Facturation Premium — F1.0 → F1.3

Documentation des chantiers **Workflow Foundation (F1.0)**, **Document Composer Premium (F1.1)** et suites catalogue / insights / live document.

## F1.0 — Workflow Foundation

| Doc | Contenu |
|-----|---------|
| [01-workflow.md](./01-workflow.md) | Étapes officielles du parcours |
| [02-information-architecture.md](./02-information-architecture.md) | Espaces & routes |
| [03-wizard-framework.md](./03-wizard-framework.md) | Framework générique |
| [04-catalog-strategy.md](./04-catalog-strategy.md) | Catalogue local |
| [05-local-vs-inventorypilot.md](./05-local-vs-inventorypilot.md) | Blueprint catalogue |
| [06-validation-engine.md](./06-validation-engine.md) | Contrôles dérivés |
| [07-preview.md](./07-preview.md) | Prévisualisation / PDF |
| [08-roadmap.md](./08-roadmap.md) | F1.0 → F1.4 |
| [09-test-plan.md](./09-test-plan.md) | FP01–FP30 |
| [10-implementation-report.md](./10-implementation-report.md) | Rapport F1.0 |

## F1.1 — Document Composer Premium

→ **[composer/](./composer/)** (README + architecture, layout, focus, preview, catalog, validation, responsive, roadmap, tests CP01–CP40, rapport)

## F1.3 — Live Document Experience

→ **[`../live-document/`](../live-document/)** — assemblage UX (preview / totaux / insights / pickers / autosave / statut). **F1.4 non démarré.**

## F1.3.4 — Document Design System + logo

→ **[`../document-design-system/`](../document-design-system/)** — template premium PDF, Identité visuelle (Avec/Sans logo) à l’étape **Vérification**, config branding unique. **F1.4 non démarré.**

## F1.3.5 — Document Studio

→ **[document-studio/](./document-studio/)** — heroes, PDF vivant, smart cards (UX shell).

## Routes

| Espace | Path |
|--------|------|
| Vue d’ensemble | `/facturation` |
| Documents | `/facturation/documents` |
| Nouveau document (Composer) | `/facturation/nouveau` |

## Code

- Wizard FW : `frontend/src/wizard-framework/`
- Composer FW : `frontend/src/composer-framework/`
- Workflow : `frontend/src/comptapilot/facturation/workflow/`
- Live document : `frontend/src/comptapilot/facturation/live-document/`
- Composer page : `frontend/src/pages/facturation/FacturationComposerPage.tsx`

## Références

- Blueprint V1 : `../platform-blueprint/`
- P0.5 UI : `../comptapilot/facturation-premium/`
