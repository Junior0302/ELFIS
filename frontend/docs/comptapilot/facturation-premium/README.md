# Facturation Premium — P0.5

Documentation du chantier **Facturation Premium** (ComptaPilot), repris après la phase P0 Blueprint.

| Doc | Contenu |
|-----|---------|
| [01-runtime-audit.md](./01-runtime-audit.md) | État runtime & livré vs manquant |
| [02-p05-plan.md](./02-p05-plan.md) | Plan P0.5 (UI premium safe) |
| [03-go-nogo.md](./03-go-nogo.md) | GO / NO GO & prochaines étapes |
| [04-changelog.md](./04-changelog.md) | Changelog de session |

**Route :** `/facturation` (vue d’ensemble) · `/facturation/documents` (CRUD fp05) · `/facturation/nouveau` (wizard F1.0)  
**Code :** `frontend/src/pages/FacturationPage.tsx` + `frontend/src/comptapilot/facturation/` + `frontend/src/wizard-framework/`  
**Suite F1.0 :** [`../../facturation-premium/`](../../facturation-premium/README.md)  
**Références :** Blueprint V1 (`platform-blueprint/`), Dashboard Premium (`dashboard-premium/`), commercial-readiness

## Marqueur runtime

`data-billing-layout="fp05"` sur le root de la page documents (CRUD).  
`data-fp-spaces="f10"` sur le layout des espaces Facturation.
