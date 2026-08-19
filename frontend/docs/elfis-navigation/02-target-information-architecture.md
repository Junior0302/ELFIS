# 02 — Architecture d’information cible

## Sections livrées (routes réelles uniquement)

### PRINCIPAL
- Accueil → `/home`
- Favoris → `/home#home-apps`
- Activité → `/home#home-activity`

### ENTREPRISE
- Organisation → `/platform/organization`
- Membres et équipes → `/platform/members` (`users.manage`)
- Rôles et permissions → `/platform/members#roles` (`users.manage`) — même surface Membres, ancre légende rôles

### DONNÉES PARTAGÉES
- Relations → `/platform/relations`
- Documents → `/platform/documents` (`documents.read`)

### PLATEFORME
- Notifications → `/notifications`
- Communications → `/platform/communications`
- Paramètres → `/platform/settings`

### OUTILS
- Intelligence ELFIS → `/platform/aura` (`ai.analysis`) — ex label « Aura »
- Recherche globale → `/search`

### SUPPORT (footer)
- Aide et support → `/home#home-status`
- Déconnexion → action `logout`
- Identité : **ELFIS** / Plateforme

## Backlog (hors menu — pas de route vide)

| Item | Raison |
|------|--------|
| Contacts | Pas de hub plateforme ; Sales `/sales/contacts` hors Core |
| Entreprises | Pas de hub plateforme ; Sales `/sales/companies` hors Core |
| Centre de santé | Health services developer/admin uniquement |
| Journal | Pas de journal plateforme ; Sales `/sales/journal` hors Core |

Pas de badge « Bientôt » : la stratégie mature `coming_soon` est celle du Launcher, pas de la nav Core.

## Hors scope NAV.CORE.1

- Menus ComptaPilot / SalesPilot (Launcher + sidebars produit)
- NAV.DOMAIN.1

