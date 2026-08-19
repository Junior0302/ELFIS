# 05 — Components

## Header premium

- Titre « Financial Command Center »
- Sync : `sync.last_sync_at` || `computed_at`
- Org : `memberships[].organization_name` (auth réel)
- Badge **Engine Ready** si overview OK ; sinon état honnête
- Source : Financial Engine
- Actions : Analyse détaillée (`/finance`), Actualiser, Exporter (toast « bientôt »)

## Health Score premium

- Grande jauge SVG
- Facteurs + barres
- Conseils depuis `recommendations` (pas inventés)
- Disclaimer comptable
- Pas d’évolution fictive (API n’expose pas d’historique score)

## Prévisions empty premium

- Illustration SVG/CSS
- CTA « Connecter une banque »
- Pas de 30/60/90 tant que l’API ne les fournit pas

## Timeline activité

- Icône dérivée du `type`
- Label, montant, badge type, meta, heure (`created_at` || `date`)
