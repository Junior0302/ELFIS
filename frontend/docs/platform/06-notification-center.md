# 06 — Notification Center

**P1.1** · Centre d’alertes **unifié** plateforme.

---

## Entrée

```
Topbar [🔔] + badge compteur
Clic → panneau droit (drawer) ou popover ancré
```

```
┌──────────────────────────┐
│ Notifications      [⚙️]  │
│ [All] [Platform] [Pilot] │
├──────────────────────────┤
│ ● Titre                  │
│   SalesPilot · il y a 2m │
│   Aperçu…                │
├──────────────────────────┤
│ ○ Titre                  │
│   Plateforme · hier      │
└──────────────────────────┘
│ Tout marquer lu          │
```

---

## Modèle item

```
Notification
├── id
├── source: platform | comptapilot | salespilot | …
├── severity: info | success | warning | danger
├── title / body
├── created_at
├── read: bool
└── deep_link: route ELFIS
```

---

## Flux clic

```
Clic notif
    │
    ├── Même Pilot  → navigate deep_link + mark read
    └── Autre Pilot → switch Pilot → deep_link + toast
                          « Ouvert dans SalesPilot »
```

---

## Filtres & groupes

```
All
├── Platform (org, billing, security)
└── By Pilot (Compta / Sales / Doc / …)
```

---

## Règles UX

| Règle | Détail |
|-------|--------|
| Un seul centre | Pas de cloche par sidebar Pilot |
| Badge | Non-lues ; max « 9+ » |
| Temps réel | Option ; sinon refresh à l’ouverture |
| Empty | Illustration minimale + copy |
| Préférences | Via icône ⚙️ → profil / settings notifs |

---

## Do / Don’t

```
DO                         DON’T
─────────────────────────  ─────────────────────────
Source Pilot visible       Notif anonyme
Deep-link fiable           Modal mort sans action
Severité = couleur système  Primary Pilot partout
```
