# 14 — Premium dashboard layout (S1.2.5.1)

## Principes

- Cartes blanches (`--ps-surface`), ombres légères, bordures discrètes.
- Vert produit en **accent uniquement** (CTA primaire, barres revenus, jauge OK).
- Titre FCC en empattement léger (serif stack) pour signal premium ; données en sans-serif UI.
- Espacement section ~1.65rem ; pas de pixel-perfect fragile.

## Ordre desktop

1. Header  
2. Bandeau org (si besoin)  
3. **Analyser** — 3 charts  
4. **Essentiel** — KPI compact (+ documents)  
5. **Décider aujourd’hui** — Priorités | Alertes | Actions  
6. **Comprendre et prévoir** — Health | Prévisions | Encaissements/décaissements  
7. **Bas** — Traiter 30% | Activité 42% | Assistant 28%

## Ordre mobile (CSS `order`)

Priorités → Alertes → Trésorerie KPI → Impayés → TVA → Actions → autres KPI → Comprendre → Graphiques → Bas.

## Variants Widget Framework

| Variant | Usage FCC |
|---|---|
| `chart` | Analyser |
| `compact` | Essentiel KPI |
| `list` | Priorités, alertes, Traiter, activité |
| `score` | Health |
| `hero` | Assistant |
| `standard` | Actions, empty forecast |

## Empty states

- Prévisions / flux : empty + CTA banque/finance — **aucun montant inventé**.
- Historique chart &lt; 2 points : message « Historique insuffisant… ».
- Écritures / rapprochements : `N/A` + « Signal non exposé par overview ».
