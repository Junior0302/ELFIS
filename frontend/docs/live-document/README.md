# Live Document Experience V1 (F1.3)

Assemblage UX des briques existantes pour un **document vivant** dans le Document Composer — **aucun nouveau Framework / moteur / IA**.

## Périmètre

| Inclut | Exclut |
|--------|--------|
| Preview live + PDF debounce | Nouveau moteur PDF / IA |
| Totaux vivants (helpers workflow) | Modification calculs métier / Billing / Vault / Financial Engine |
| Insights dérivés (Insight Framework) | Données inventées (similarité, favoris fictifs) |
| Pickers in-composer (Smart Library / Search) | F1.4 |
| Autosave / statut / a11y / perf polish | Refonte API |

## Docs

| Fichier | Contenu |
|---------|---------|
| [01-runtime-audit.md](./01-runtime-audit.md) | Points interactifs & gaps comblés |
| [02-live-preview.md](./02-live-preview.md) | Aperçu réactif |
| [03-live-totals.md](./03-live-totals.md) | Totaux & échéance |
| [04-live-insights.md](./04-live-insights.md) | Insights réels |
| [05-status.md](./05-status.md) | Statuts document |
| [06-autosave.md](./06-autosave.md) | UX autosave |
| [07-performance.md](./07-performance.md) | Memo / debounce / lazy |
| [08-accessibility.md](./08-accessibility.md) | ARIA live |
| [09-tests.md](./09-tests.md) | LD01–LD40 |
| [10-implementation-report.md](./10-implementation-report.md) | Rapport GO |

## Code

- Helpers : `frontend/src/comptapilot/facturation/live-document/`
- Page : `FacturationComposerPage.tsx`
- Preview / status : `composer-framework/`
- Insights : `insight-framework/`
- Pickers : `platform-search/` + Resource Library

## STOP

**F1.3 livré — ne pas commencer F1.4 dans ce chantier.**
