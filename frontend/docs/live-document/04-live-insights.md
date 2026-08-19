# 04 — Live insights

## Contrat

Utilise **Insight Framework** (`InsightList` / mappers). Contenu **uniquement** dérivable du draft + métadonnées catalogue réelles.

| Insight | Condition |
|---------|-----------|
| Client sélectionné | `client.displayName` |
| Produit ajouté | ≥ 1 ligne libellée |
| TVA inhabituelle | hors 0 / 5,5 / 10 / 20 % (standards FR) |
| Montant élevé | HT > 50 000 (même seuil que controls) |
| Produit récent | `catalogCreatedAt` ≤ 30 j. si fourni |
| Document similaire | **Absent** — pas d’historique API |

Validation Composer reste mappée via `mapComposerIssuesToInsights` (doublons montant/TVA live filtrés).

Apparition progressive : `LiveInsightsPanel` (stagger), respect reduced-motion via CSS transitions absentes.
