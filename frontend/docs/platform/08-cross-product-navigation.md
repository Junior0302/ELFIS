# 08 — Cross-Product Navigation

**P1.1** · Passer d’un Pilot à l’autre sans casser la plateforme.

---

## Modèle mental

```
ELFIS Core (session + org)
    │
    ├── ComptaPilot
    ├── SalesPilot
    ├── DocPilot
    └── …
```

Un seul **Product Shell** monté ; les autres restent accessibles via launcher / search / deep-links.

---

## Mécanismes de bascule

| Mécanisme | Usage |
|-----------|--------|
| **App Launcher** | Choix explicite d’app |
| **Global Search** | Aller à une entité autre Pilot |
| **Notification** | Deep-link cross-Pilot |
| **Liens métier** | Ex. « Voir facture » depuis Sales (si droit) |
| **Récents launcher** | Retour rapide |

```
Sales ──launcher──► Compta
Sales ──search────► Doc entité
Sales ──notif─────► Platform admin
Sales ──link──────► Compta facture
```

---

## Ce qui change / ne change pas

```
CHANGE                      NE CHANGE PAS
─────────────────────────   ─────────────────────────
Primary / accent Pilot      Session user
Wordmark Product            Org active
Sidebar métier              Position topbar chrome
Workspace routes            Mark géométrie
Teinte Mark                 Search / Notif / Profil
```

---

## Pattern deep-link

```
URL conceptuelle
/app/{pilot}/{module}/...

Exemples
/app/salespilot/opportunities/123
/app/comptapilot/invoices/456
```

Switch :

```
resolve pilot from URL
  → set product theme
  → mount Product Shell
  → navigate module
  → keep Platform Shell
```

---

## Hub sans Pilot

```
/app  ou  /hub
    │
    ▼
Empty / launcher plein écran
« Choisir une application »
```

---

## Arbre navigation globale

```
Platform
├── Hub
├── Launcher → Pilot*
│              ├── modules Pilot (sidebar)
│              └── deep entities
├── Search → any
├── Notifs → any
└── Profile / Org / Admin
```

---

## Erreurs & droits

| Cas | UX |
|-----|-----|
| Pas d’accès Pilot | Tuile disabled + tooltip / CTA admin |
| Deep-link interdit | Toast + rester Pilot courant / hub |
| Pilot inconnu URL | Redirect hub |

---

## Do / Don’t

```
DO                            DON’T
────────────────────────────  ────────────────────────────
Toast discret après switch    Recharger login
Préserver org                 Reset org à chaque Pilot
URL partageable               État seulement en mémoire
```
