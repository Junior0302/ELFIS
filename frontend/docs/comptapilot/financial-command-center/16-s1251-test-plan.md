# 16 — Plan de tests manuels S1.2.5.1 (FV01–FV20)

Tous les items sont **À tester manuellement** sur `/dashboard` (org avec entitlement financier).

| ID | Scénario | Attendu | Statut |
|---|---|---|---|
| FV01 | Chargement org avec data | Header + 5 sections dans l’ordre Analyser→…→Bas | À tester manuellement |
| FV02 | Org incomplete | Bandeau discret + lien `/platform/organization` | À tester manuellement |
| FV03 | Charts ≥ 2 périodes | 3 graphiques lisibles, légendes, tooltips | À tester manuellement |
| FV04 | Charts 1 période | Message historique insuffisant, pas de courbe fictive | À tester manuellement |
| FV05 | Charts vides | Empty widgets Analyser, pas de crash | À tester manuellement |
| FV06 | Essentiel KPI | Rangée compacte, tendance ou « Comparaison indisponible » | À tester manuellement |
| FV07 | Sync hors Essentiel | Aucune carte sync dans Essentiel | À tester manuellement |
| FV08 | Sync dans Traiter | Statut sync overview visible dans Traiter | À tester manuellement |
| FV09 | Docs | Présent Essentiel + compteur Traiter ; pas de 3ᵉ doublon KPI | À tester manuellement |
| FV10 | Décider | 3 colonnes Priorités / Alertes / Actions | À tester manuellement |
| FV11 | Comprendre 3 cols | Health colonne + 2 empties prévisions/flux | À tester manuellement |
| FV12 | Pas de chiffres maquette | Aucun 15420 € / montants fictifs forecast | À tester manuellement |
| FV13 | Bas proportions | Traiter ~30% / Activité ~42% / Assistant ~28% (desktop) | À tester manuellement |
| FV14 | Écritures / rapprochements | N/A si absents overview | À tester manuellement |
| FV15 | Refresh global | « Actualiser tout » recharge sans quitter `/dashboard` | À tester manuellement |
| FV16 | Refresh widget | Icône refresh aria-label fonctionne | À tester manuellement |
| FV17 | Lien `/finance` | « Analyse détaillée » | À tester manuellement |
| FV18 | Mobile &lt; 720px | Priorités métier avant graphiques | À tester manuellement |
| FV19 | a11y clavier | Tab sur refresh, liens, CTAs | À tester manuellement |
| FV20 | Régression `/finance` | Page finance inchangée fonctionnellement | À tester manuellement |

## Automatisé

Voir `FinancialCommandCenter.test.tsx` + `widget-framework.test.tsx` (ordre sections, sync, empty, historique, refresh, a11y basique).
