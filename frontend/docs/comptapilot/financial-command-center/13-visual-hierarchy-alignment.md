# 13 — Alignement hiérarchie visuelle (S1.2.5.1)

**Date :** 2026-08-02  
**Référence :** maquette layout FCC (valeurs fictives **non** reprises)

## Matrice

| Élément maquette | Composant actuel (S1.2.5) | Écart | Correction S1.2.5.1 | Cible | Risque |
|---|---|---|---|---|---|
| Header titre + résumé + MAJ + CTAs | `fcc-header` | Sous-titre légèrement différent | Aligné « Vue d’ensemble… » | Header premium | Faible |
| Bandeau org incomplete | `fcc-banner` | OK | Conservé discret | Conditionnel | Faible |
| ANALYSER 3 charts en haut | Section Analyser **en bas** | Ordre inversé | Section **Analyser** en 1ʳᵉ position contenu | Charts 210–280px | Moyen (empty charts) |
| ESSENTIEL 8 KPI compact | KPI + docs, sync ailleurs | Sync parfois confondu / ordre | KPI + docs uniquement, variant `compact` | Rangée 8 cols | Moyen (nb KPI variable) |
| DÉCIDER 3 colonnes | Présent après Essentiel | OK structure, position | Après Essentiel | Priorités / Alertes / Actions | Faible |
| COMPRENDRE 3 cols | Health full-width + Prévoir séparé | Health full width ; pas de col flux | Grille 3 : Health · Prévisions empty · Flux empty | Colonnes égales | Faible |
| BAS 30/42/28 | Traiter+activité côte à côte, Assistant séparé | Proportions absentes | `fcc-bottom-grid` 30/42/28 | Traiter / Activité / Assistant | Faible |
| Sync dans Traiter | Sync widget séparé | Sync hors Traiter compact | Bloc sync dans carte Traiter | Compteurs overview | Faible |
| Écritures / rapprochements | Absents | Maquette les montre | N/A honnête si champ overview absent | Pas d’invention | Faible |
| Refresh discret | Bouton « Actualiser » visible | Trop dominant | Icône + aria-label, label compact masqué | a11y | Faible |
| Footer source | Meta footer standard | Trop présent | `ew-footer--secondary` | Secondaire | Faible |
| Cartes blanches / ombre légère | Bordure seule | Manque profondeur | Ombre soft framework | Premium | Faible |
| Mobile priorités métier | Décider remonte | KPI/charts non priorisés | Orders CSS sections + classes `fcc-m-*` | RWD | Moyen |

## Règles non négociables

- Aucune valeur maquette (ex. 15 420 €) inventée.
- Sources = `financialApi.overview` uniquement.
- `/finance` métier non modifié.
- STOP S1.3.
