# 01 — Runtime audit (S1.2.5)

Audit des surfaces liées au dashboard financier avant / après branchement FCC.

| Bloc | Route | Composant | API | Donnée réelle \| mock | Propriétaire | Réutilisable | Risque | Décision |
|---|---|---|---|---|---|---|---|---|
| Accueil Compta | `/dashboard` | `DashboardPage` → `FinancialCommandCenter` | `financialApi.overview` | Réelle (Financial Engine) | ComptaPilot | Non (page produit) | Faible — deep links inchangés | **Remplacé** : FCC = vraie home |
| Analyse finance | `/finance` | `FinancialDashboardPage` | `financialApi.*` | Réelle | ComptaPilot | Non | Faible | **Conservé** analyse détaillée |
| Widget shell | n/a | `WidgetContainer` + sous-composants | n/a | n/a | ELFIS (framework) | Oui | Faible | **Introduit** V1 |
| Priorités | n/a | `priorities.ts` | dérivé overview | Réelle (signaux API) | ComptaPilot | Oui (logique pure) | Moyen si invente | **OK** — signaux API only |
| Launch onboarding | (ex-dashboard) | `LaunchDashboard` | `api.getLaunchDashboard` | Réelle | ComptaPilot / Core | Oui | Moyen UX clutter | **Retiré** du `/dashboard` Compta |
| Command Center Compta | (ex-dashboard) | `components/CommandCenter` | `api.getCommandCenter` | Réelle | ComptaPilot | Oui | Faible | **Retiré** du `/dashboard` (global CC intact) |
| Bandeau org | `/dashboard` | bandeau FCC | `getLaunchDashboard.workspace_ready` | Réelle | Core → org | Oui | Faible | **Garder** → `/platform/organization` |
| Home mapping legacy | n/a | `dashboardHome.ts` | overview | Réelle | ComptaPilot | Oui | Faible | **Conservé** pour `/finance` / helpers ; plus utilisé par home |
| Nav Dashboard | nav | `navModel` | n/a | n/a | Shell | Oui | Faible | Inchangé (`/dashboard`) |
| Product entry | launcher | `productEntryRoutes` | n/a | n/a | Shell | Oui | Faible | Inchangé → `/dashboard` |
| Sales home | `/sales` | `SalesDashboardPage` | sales APIs | Réelle | SalesPilot | Non | — | **Ne pas toucher** |
| Launcher | overlay | `AppLauncher*` | n/a | n/a | Core | Oui | — | **Ne pas toucher** |
| Command Center global | `/home` etc. | `platform-command` | n/a | n/a | Core | Oui | — | **Ne pas toucher** |
| Forecast | section FCC | widget empty | *aucun* dans `financialApi` | Empty pro | ComptaPilot | Oui | Invention data | **Empty** — pas d’invention |
| Charts | section Analyser | MiniBar / SparkLine | `overview.charts` | Réelle si présentes | Engine | Oui | Faible | Brancher si champs présents |

## Compatibilité deep links

- `/dashboard` reste l’URL d’entrée ComptaPilot (favoris, `state.from`, back).
- `/finance` inchangé.
- `/organisation` → redirect existant vers `/platform/organization`.
- Aucun rename de route SPA.
