# 05 — Continuer / Reprendre

## Source

`elfis_last_product` + `elfis_last_product_at` uniquement (pas d’historique inventé).

## Libellés

| Cas | UI |
|-----|-----|
| lastProduct → espace | **Reprendre dans {Espace}** |
| Aucun lastProduct | **Commencer dans Finance** (fallback) |

## Méta (si données réelles)

- Signature moteur (discret)
- Horodatage relatif (`formatSpaceActivity`)
- État « Espace actif » si applicable

## Mapping produit → espace

| lastProduct | Espace |
|-------------|--------|
| comptapilot | Finance |
| salespilot | Commercial |
