# Smart cards

## Règle d’or

**Uniquement des données réelles du draft.** Si le champ n’existe pas côté API / draft → omettre. Ne jamais inventer ★★★★★, CA, dates fictives, scores.

## Client (`StudioClientSmartCard`)

Affiché après sélection :

- Nom (`displayName`) — toujours
- E-mail / tél. / adresse — **seulement si non vides**

Pas de : score relation, historique, dernier achat (non fournis).

## Produits (`StudioProductsSmartCard`)

Affiché si ≥ 1 ligne avec libellé :

- Compteur de lignes
- Libellé, qté × prix, total ligne (calcul local existant)
- Truncation +N au-delà de 4

Si aucune ligne libellée → composant retourne `null` (vide intelligent).

## Markers

- `data-ds-smart-card="client|products"`
