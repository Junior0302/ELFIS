# 11 — Plan de tests (FC01–FC25)

Statuts initiaux : **À tester manuellement** (sauf tests unitaires automatisés listés en bas).

| ID | Scénario | Statut |
|---|---|---|
| FC01 | `/dashboard` affiche le FCC (pas LaunchDashboard) | À tester manuellement |
| FC02 | Aucun parcours onboarding ELFIS sur `/dashboard` | À tester manuellement |
| FC03 | Lien « Analyse détaillée » → `/finance` | À tester manuellement |
| FC04 | `/finance` reste accessible et inchangé fonctionnellement | À tester manuellement |
| FC05 | Deep link favori `/dashboard` après login | À tester manuellement |
| FC06 | `state.from` login vers `/dashboard` | À tester manuellement |
| FC07 | Browser back depuis `/finance` vers `/dashboard` | À tester manuellement |
| FC08 | Bandeau org incomplete → `/platform/organization` | À tester manuellement |
| FC09 | KPI affichent valeurs Engine (pas inventées) | À tester manuellement |
| FC10 | Empty KPI / has_data=false message honnête | À tester manuellement |
| FC11 | Priorités dérivées alertes / impayés / docs / sync | À tester manuellement |
| FC12 | Alertes Engine affichées ; empty correct | À tester manuellement |
| FC13 | Actions rapides uniquement compta/finance | À tester manuellement |
| FC14 | Health Score + disclaimer visible | À tester manuellement |
| FC15 | Health setup → empty professionnel | À tester manuellement |
| FC16 | Prévisions : empty (pas de chiffres inventés) | À tester manuellement |
| FC17 | Charts branchés si `overview.charts` rempli | À tester manuellement |
| FC18 | Refresh global sans reload page | À tester manuellement |
| FC19 | Refresh widget sans reload page | À tester manuellement |
| FC20 | Entitlement absent → message abonnement | À tester manuellement |
| FC21 | Erreur API → retry | À tester manuellement |
| FC22 | Mobile : Décider prioritaire | À tester manuellement |
| FC23 | A11y basique titres / boutons | À tester manuellement |
| FC24 | SalesPilot / Launcher / CC global non régressés | À tester manuellement |
| FC25 | Product entry Compta reste `/dashboard` | À tester manuellement |

## Automatisé (vitest)

- Widget framework : états, retry, a11y labels
- FCC : pas d’onboarding, KPI, empty, refresh, route export DashboardPage
- `priorities.ts` : mapping signaux
- `tsc -b` + `vite build`
