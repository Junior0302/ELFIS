# 19 — ComposerDialog Layout

## Rôle

Grande surface modale (`ComposerDialog`) accueillant `ComposerFocusLayout` + freeform existant.

## Dimensions

| Viewport | Largeur | Hauteur |
|----------|---------|---------|
| Desktop | `clamp(1100px, 94vw, 1700px)` | ~92vh |
| Laptop (≤1280) | 96vw | 94vh |
| Tablette / mobile (≤900) | 100vw | 100vh (plein écran) |

Radius + ombre distincts de la petite pop-in type (`fp-create-flow--type` vs `--composer`). Transition taille 180ms.

## Structure interne

- Header sticky : retour Documents, titre, type, statut, autosave, ≤2 secondaires + 1 primaire (via `ComposerFocusLayout`)
- **F1.3.2 (modal)** : progression horizontale 6 `ComposerStep` ; editor ~62% | preview ~38% sticky ; footer Retour/Continuer
- Workspace page mode : Editor ~65% scrollable | Preview ~35% sticky (freeform)
- Scroll **interne** uniquement ; page Documents inert + scroll lock Overlay Manager
- Confirmation post-création **dans** le dialog
