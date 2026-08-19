# 08 — Test plan F1.3.2.3

## Automatisés (RR01–RR40)

Fichier : `src/platform-routing/refresh-route-persistence.test.tsx` (+ `returnPath.test.ts`).

| ID | Cas |
|----|-----|
| RR01–RR05 | sanitizeReturnPath / locationReturnKey |
| RR06–RR10 | resolveProductPhase loading / entitled / admin |
| RR11 | loading → BootstrapLoadingScreen |
| RR12–RR21 | routes métier / platform / home / sales sans bounce Home |
| RR22 | erreur subscription → message |
| RR23 | org inaccessible |
| RR24 | no_entitlement → public welcome (pas Home) |
| RR25 | welcome + from → restore route |
| RR26–RR28 | RequireAuth loading / login from / outlet |
| RR29–RR30 | sanitize edge cases |
| RR31–RR40 | matrice routes, admin, public paths, modal, org vide |

## Manuels RF01–RF20 — À tester manuellement

| ID | Scénario |
|----|----------|
| RF01 | F5 sur `/dashboard` → reste dashboard |
| RF02 | F5 sur `/facturation/documents` |
| RF03 | F5 sur `/facturation/documents/new?type=invoice` → Documents + Composer |
| RF04 | F5 sur `/finance` |
| RF05 | F5 sur `/accounting/proposals` |
| RF06 | F5 sur `/platform/relations` |
| RF07 | F5 sur `/platform/documents` |
| RF08 | F5 sur `/copilote` |
| RF09 | F5 sur `/settings` |
| RF10 | Pendant bootstrap : écran chargement, **pas** flash Home |
| RF11 | Session expirée → login → retour route d’origine |
| RF12 | Back/forward après navigation multi-pilotes |
| RF13 | Deep link collé dans barre d’adresse (auth OK) |
| RF14 | Org switch puis F5 → même org |
| RF15 | URL inconnue → 404 (pas Landing/Home auto) |
| RF16 | Couper réseau au refresh → erreur + Réessayer |
| RF17 | Redirect legacy `/vault` → platform documents |
| RF18 | `/quotes` → `/devis` conservé |
| RF19 | Sales `/sales/pipeline` F5 |
| RF20 | Après login depuis `/finance` → `/finance` |
