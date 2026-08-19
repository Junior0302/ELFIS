# 08 — Plan de tests EH01–EH30

Fichier : `frontend/src/app-launcher/elfis-spaces.eh.test.tsx`

| ID | Contrôle |
|----|----------|
| EH01 | Trigger **Espaces** (pas Applications) |
| EH02 | Titre + sous-titre métiers |
| EH03 | 6 espaces catalogue |
| EH04 | Routes Finance / Commercial / Documents |
| EH05 | RH / Analyse / Support → Bientôt |
| EH06 | Pas de carte ELFIS Core app |
| EH07 | Signatures moteurs |
| EH08 | Commencer dans Finance (fallback) |
| EH09 | Reprendre dans Commercial (lastProduct) |
| EH10 | Alias facture → Finance |
| EH11 | Alias pipeline → Commercial |
| EH12 | Footer Accueil ELFIS |
| EH13 | Accueil header + footer |
| EH14 | Cartes communes `data-space` |
| EH15 | Accents domaines |
| EH16 | Routes SPA connues |
| EH17 | Finance / Commercial / Documents ouvrables |
| EH18 | Badge Bientôt |
| EH19 | Raccourcis Finance |
| EH20 | Raccourcis Commercial |
| EH21 | Placeholder recherche |
| EH22 | Empty search |
| EH23 | Ctrl+Shift+A |
| EH24 | Escape + focus |
| EH25 | Ouvrir Finance ferme dialog |
| EH26 | Espace actif Finance |
| EH27 | Pas de libellé Applications dans panel |
| EH28 | Docs `elfis-spaces/` présentes |
| EH29 | Exports module |
| EH30 | Cohérence routes catalogue (+ `tsc` / `build` npm) |

EH30 build/tsc exécutés localement via `npm run build` / `tsc -b` (rapport 09).
