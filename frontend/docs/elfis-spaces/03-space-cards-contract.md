# 03 — Contrat cartes espaces

## Composant unique

`LauncherProductCard` — toutes les cartes domaines (ouvertes ou Bientôt).

## Contenu obligatoire

| Champ | Règle |
|-------|--------|
| Titre | Nom d’espace (Finance, Commercial…) |
| Description | Une phrase métier |
| Accent | CSS `--launcher-card-accent` domaine |
| Signature | `Moteur X` discret (si défini) |
| Raccourcis | Liens routes réelles (max 3) si ouvrable |
| Action | `Ouvrir {Espace}` / `Ouvert` / `Bientôt` |
| Badge | `Bientôt` / `Espace actif` / `Dernière visite` |

## Interdit

- Titre produit (ComptaPilot) en hero de carte
- « by ELFIS Core »
- « Application active » (remplacé par Espace actif)
- Navigation vers route absente
