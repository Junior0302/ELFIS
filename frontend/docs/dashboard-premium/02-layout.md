# 02 — Layout

## Ordre desktop

1. **Header** premium (titre, meta sync/org/engine, actions)
2. Bandeau org incomplete (conditionnel)
3. **Analyser**
   - Revenus vs dépenses — **full width** (héros)
   - Trésorerie **1/2** | Évolution CA **1/2**
4. **Essentiel** — grille KPI uniforme (+ docs ; banques si signal sync réel)
5. **Décider aujourd’hui** — Priorités | Alertes | Actions
6. **Comprendre et prévoir** — Health | Prévisions | Flux
7. **Bas** — Traiter (~30%) | Activité timeline (~42%) | Assistant (~28%)

## Structure Analyser (CSS)

```
.fcc-charts-layout
  ├── .fcc-chart--hero   (grid full)
  └── .fcc-charts-half   (ew-grid--2)
```

## Mobile (`max-width: 720px`)

CSS `order` : Décider → Essentiel → Comprendre → Analyser → Bas.  
Priorités métier avant graphiques.
