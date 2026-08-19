# Financial Command Center V1 + ELFIS Widget Framework V1 (S1.2.5 → **S1.2.6**)

**Date :** 2026-08-02  
**Produit :** ComptaPilot  
**Route d’accueil :** `/dashboard`  
**Analyse détaillée :** `/finance`

## Objectif

Remplacer l’accueil onboarding / LaunchDashboard de ComptaPilot par un **Financial Command Center** orienté décision, alimenté uniquement par le **Financial Engine** (`financialApi`), avec un **Widget Framework** générique réutilisable.

**S1.2.6 — Premium V2** : polish présentation (header, layout Analyser héros, KPI, timeline, health, empty prévisions) — **aucune valeur fictive**, aucune API nouvelle.

Docs premium dédiées : [`../../dashboard-premium/`](../../dashboard-premium/).

## Livrables

| Zone | Emplacement |
|---|---|
| FCC | `frontend/src/comptapilot/financial-command-center/` |
| Widget Framework | `frontend/src/widget-framework/` |
| Entrée `/dashboard` | `frontend/src/pages/DashboardPage.tsx` → re-export FCC |
| Docs S1.2.5.x | ce dossier |
| Docs Premium S1.2.6 | `frontend/docs/dashboard-premium/` |
| Tests | `*.test.tsx` sous widget-framework et financial-command-center |

## Sections FCC (S1.2.6)

1. Header premium — sync, org, Engine Ready, source, Analyse / Actualiser / Exporter  
2. Bandeau org incomplete (conditionnel) → `/platform/organization`  
3. **Analyser** — Revenus vs dépenses (full) + Trésorerie | Évolution CA  
4. **Essentiel** — KPI compact + documents (+ banques si signal sync)  
5. **Décider aujourd’hui** — priorités | alertes | actions rapides  
6. **Comprendre et prévoir** — Health | Prévisions empty premium | Flux empty  
7. **Bas** — Traiter (~30%) | Activité timeline (~42%) | Assistant (~28%)

## Hors périmètre (STOP S1.3)

- Pas de nouveau moteur financier, pas d’IA dédiée, pas de tables DB  
- Pas de modification SalesPilot / Launcher / Command Center global  
- Pas d’onboarding ELFIS sur le dashboard Compta

## Index documentation

| Fichier | Contenu |
|---|---|
| [01-runtime-audit.md](./01-runtime-audit.md) | Matrice runtime |
| [02-vision.md](./02-vision.md) | Vision produit |
| [03-information-architecture.md](./03-information-architecture.md) | IA / sections |
| [04-widget-framework.md](./04-widget-framework.md) | Framework |
| [05-widget-contract.md](./05-widget-contract.md) | Contrat widget |
| [06-priorities.md](./06-priorities.md) | Priorités du jour |
| [07-alerts.md](./07-alerts.md) | Alertes |
| [08-financial-health-score.md](./08-financial-health-score.md) | Health score |
| [09-performance.md](./09-performance.md) | Perf / refresh |
| [10-responsive-accessibility.md](./10-responsive-accessibility.md) | RWD / a11y |
| [11-test-plan.md](./11-test-plan.md) | Plan FC01–FC25 |
| [12-implementation-report.md](./12-implementation-report.md) | Rapport S1.2.5 |
| [13-visual-hierarchy-alignment.md](./13-visual-hierarchy-alignment.md) | Matrice maquette S1.2.5.1 |
| [14-premium-dashboard-layout.md](./14-premium-dashboard-layout.md) | Layout premium |
| [15-chart-presentation.md](./15-chart-presentation.md) | Graphiques Analyser |
| [16-s1251-test-plan.md](./16-s1251-test-plan.md) | FV01–FV20 manuels |
| [17-s1251-implementation-report.md](./17-s1251-implementation-report.md) | Rapport GO/NO GO |
| [Dashboard Premium S1.2.6](../../dashboard-premium/01-overview.md) | Overview Premium V2 |
| [DP01–DP40](../../dashboard-premium/08-dp01-dp40-manual-test-plan.md) | Plan manuel Premium |
