# 09 — Plan de tests Composer (CP01–CP40)

**À tester manuellement** sauf mention « auto ».

## Framework (CP01–CP08)

| ID | Cas | Mode |
|----|-----|------|
| CP01 | Export primitives Composer | Auto |
| CP02 | Rendu layout + progressbar a11y | Auto |
| CP03 | Sidebar états terminé/en cours/bloqué | Auto |
| CP04 | onSelectStep navigation | Auto |
| CP05 | Preview empty/loading/error/ready | Auto |
| CP06 | Validation suggestion + empty | Auto |
| CP07 | Focus mode toggle + hideSecondaryNav | Auto |
| CP08 | Slots sidebar/editor/preview desktop | Auto |

## Focus & layout (CP09–CP16)

| ID | Cas | Mode |
|----|-----|------|
| CP09 | `/nouveau` masque nav espaces | Auto + manuel |
| CP10 | Sortie Dashboard | Manuel |
| CP11 | Sortie Documents | Manuel |
| CP12 | Sortie document créé | Manuel |
| CP13 | Header max 2 primaires + Annuler | Manuel |
| CP14 | Progression étapes 10 | Manuel |
| CP15 | Inspector totaux HT/TVA/TTC | Manuel |
| CP16 | Reduced motion | Manuel |

## Client / produits (CP17–CP26)

| ID | Cas | Mode |
|----|-----|------|
| CP17 | Recherche clients billing | Manuel |
| CP18 | SharedRelation clients | Manuel |
| CP19 | Créer client API | Manuel |
| CP20 | Affichage adresse/email si réels | Manuel |
| CP21 | Catalogue local | Manuel |
| CP22 | Favoris empty honnête | Manuel |
| CP23 | Plus vendus empty honnête | Manuel |
| CP24 | Créer produit local | Manuel |
| CP25 | Lignes Dupliquer/Supprimer/Déplacer | Manuel |
| CP26 | Remise % impacte total local | Manuel |

## Preview / save / validation (CP27–CP34)

| ID | Cas | Mode |
|----|-----|------|
| CP27 | Preview structuré avant save | Manuel |
| CP28 | PDF blob après brouillon | Manuel |
| CP29 | Download PDF API existante | Manuel |
| CP30 | Autosave UI après 1er brouillon | Manuel |
| CP31 | Erreur save + Réessayer | Manuel |
| CP32 | Contrôles F1.0 dans inspector | Manuel |
| CP33 | Envoyer via billingAction | Manuel |
| CP34 | Prefill `?customer_id=` | Manuel |

## Responsive & régression (CP35–CP40)

| ID | Cas | Mode |
|----|-----|------|
| CP35 | Laptop sidebar compacte | Manuel |
| CP36 | Tablette preview dessous | Manuel |
| CP37 | Mobile preview plein écran | Manuel |
| CP38 | `/facturation/documents` CRUD intact | Manuel |
| CP39 | Redirects catalogue/activite | Manuel |
| CP40 | Aura placeholders visibles (pas d’IA) | Manuel |
