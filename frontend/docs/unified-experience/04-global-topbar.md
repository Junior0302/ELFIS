# 04 — GlobalTopbar

## Ordre (inchangé, brief)

`[hamburger ELFIS][Apps/Launcher][ELFIS Core → /home][pastille Pilot][search][org][notifs][profil]`

## Règles Vague 1

| Règle | Implémentation |
|-------|----------------|
| Navy | `.ps-shell > .ps-topbar` + `--platform-shell-bg` |
| Pastille Pilot | `ProductIndicator` si `chrome.showProductIndicator` |
| Un hamburger | UI.P2 — ouvre `GlobalNavigationDrawer` ; **pas** toggle sidebar |
| Nav produit mobile | Contrôle distinct dans le viewport |

Alias : `GlobalTopbar` → `PlatformTopBar`.
