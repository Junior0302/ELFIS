# 06 — Plan de tests NC01–NC30

Fichier : `frontend/src/platform-shell/global-nav/elfis-navigation.nc.test.tsx`

| ID | Contrôle |
|----|----------|
| NC01 | Sections visibles (Principal… Outils) |
| NC02 | Ordre des sections |
| NC03 | Accueil → `/home` |
| NC04 | Favoris → `/home#home-apps` |
| NC05 | Activité → `/home#home-activity` |
| NC06 | Organisation |
| NC07 | Membres et équipes |
| NC08 | Rôles et permissions |
| NC09 | Contacts — backlog, absent du menu |
| NC10 | Entreprises — backlog, absent |
| NC11 | Relations |
| NC12 | Documents |
| NC13 | Notifications |
| NC14 | Communications |
| NC15 | Paramètres |
| NC16 | Intelligence ELFIS |
| NC17 | Centre de santé — backlog |
| NC18 | Journal — backlog |
| NC19 | Recherche globale |
| NC20 | Aide et support |
| NC21 | Déconnexion |
| NC22 | Même config sidebar / drawer |
| NC23 | Pictogrammes (ids mapping) |
| NC24 | Permissions (members / documents / aura) |
| NC25 | État actif |
| NC26 | Collapse (labels / headings masqués) |
| NC27 | Tooltips collapse |
| NC28 | Mobile = drawer même config |
| NC29 | TypeScript (`tsc -b`) |
| NC30 | Build (`vite build` via `npm run build`) |

NC29–NC30 exécutés en CI / local via scripts npm (assertés dans le rapport 07).

