# PDF vivant

## Objectif

Structure document **toujours visible** même sans données — jamais un aperçu « vide cassé ».

## Skeleton permanent

1. Logo (placeholder dashed)
2. Titre type + numéro (ou « N° — (brouillon) »)
3. Bloc client (placeholder ou données)
4. Tableau prestations (ligne skeleton ou lignes réelles)
5. Totaux HT / TVA / TTC
6. Conditions + notes
7. Footer « Document ComptaPilot · Aperçu live »

## Micro-animations

- Blocs `data-filled="true"` : fade/rise ~200ms
- Lignes remplies : fade-in
- Reduced-motion : off

## Composant

`StudioLivingPdf` — `data-ds-pdf-skeleton="1"` + `data-live-preview="structured"`

Mode PDF iframe réel inchangé (toolbar Live / PDF).
