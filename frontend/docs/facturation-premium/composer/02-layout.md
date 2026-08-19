# 02 — Layout

## Desktop

| Zone | Largeur cible |
|------|----------------|
| Sidebar étapes | ~20 % |
| Éditeur | ~50 % (corps + inspector sous/dans éditeur) |
| Preview | ~30 % |

CSS : `.elf-cmp__layout--sidebar.elf-cmp__layout--preview` → `20% / 1fr / 30%`.

## Header

- Nom document / type / statut
- Dernière sauvegarde (`ComposerStatus` autosave)
- Progression
- Max 2 actions primaires (Brouillon / Enregistrer / Envoyer selon état)
- Annuler secondaire

## Sensation

Édition de document (composer), pas déclaration admin multi-formulaires.
