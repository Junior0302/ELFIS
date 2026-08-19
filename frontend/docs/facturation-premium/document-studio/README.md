# Document Studio V1 — Vision (F1.3.5)

Transformer le Guided Modal Composer en **Document Studio** premium : sensation de construire un document professionnel progressivement.

## Principes

- Respiration, vide intentionnel, hiérarchie claire
- Studio ≠ formulaire admin
- Enrichir la présentation — **ne pas réécrire** le Composer ni la logique métier
- Données honnêtes : smart cards = champs réels uniquement (pas de scores / CA inventés)

## Périmètre

| Inclus | Exclus |
|--------|--------|
| Heroes par étape | API / backend |
| Design system studio (tokens CSS) | Workflow / routes |
| Stepper vivant ○ ◐ ✓ | Catalogue / moteurs IA |
| PDF skeleton vivant | Comptabilité |
| Smart cards (data réelle) | F1.4 |
| Conseil ComptaPilot placeholder | |

## Surfaces

- Modal guided (`presentation="modal"`) → classes `ds-studio` / `elf-cmp-focus--studio`
- Mode page freeform legacy inchangé (hors studio)

## Livrables code

- `src/comptapilot/facturation/document-studio/` — parts UI + CSS
- Microcopy `COMPOSER_GUIDED_STEPS`
- Enrichissement `FacturationComposerPage` (guided body + preview)
- Docs + tests smoke DS01+
