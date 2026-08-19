# 06 — Moteur de validation (contrôles)

## Périmètre F1.0

Fonction pure `deriveWizardControls(draft)` — **uniquement** état wizard réel.

## Contrôles possibles

- Type document manquant
- Client manquant / e-mail manquant
- Produits absents / prix à 0
- TVA hors plage / TVA 0 %
- Montant HT inhabituel (> 50 000 €) — info, non bloquant

## Non livré (pas d’invention)

- Document similaire (nécessite historique API dédié dans le wizard)
- Scoring risque client
- Blocage hard systématique

## UI

`WizardValidation` — empty : « Aucun contrôle à signaler ».
Continuer possible sauf garde-fous navigation étapes 1–3.
