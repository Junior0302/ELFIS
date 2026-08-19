# 05 — Choix logo (étape Vérification)

## UI

Section **Identité visuelle** dans le Guided Composer (`review`) :

- Segmented radio : **Avec logo** / **Sans logo** (pas de checkbox ambiguë)
- Default : préférence org `documents_show_logo` si définie, sinon Avec si logo présent, sinon Sans
- Stocké sur le **draft** : `documentBranding.showLogo` → persisté `branding_json`
- Live update immédiat ; layout sans trou (nom fort si sans logo)

## Sans logo configuré

Message + **Ajouter un logo** (sous-dialog Composer) / **Continuer sans logo**.

Upload : formats/MIME/taille via validation org existante. SVG : accepté à l’upload ; PDF = raster/miniature seulement.

## Préférence globale

Case **décochée par défaut** : « Utiliser ce choix par défaut pour les prochains documents »  
→ écrit `organizations.documents_show_logo` **seulement** si cochée + `settings.manage`.
