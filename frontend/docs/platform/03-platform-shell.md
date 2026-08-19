# 03 — Platform Shell

**P1.1** · Cadre commun ELFIS Core (navy / neutres).  
Réf. Brand : `07-platform-vs-product.md`.

---

## Composition

```
┌──────────────────────────────────────────────────────────────┐
│ PLATFORM TOPBAR                                              │
│ [Mark] [Launcher] ………… [Search] [Org] [Notif] [Profil]      │
├──────────────┬───────────────────────────────────────────────┤
│ PRODUCT      │                                               │
│ SHELL        │           WORKSPACE                           │
│ (Pilot)      │                                               │
│              │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

Mobile :

```
┌─────────────────────────┐
│ [☰ Launch] [Mark] [⋯]   │
├─────────────────────────┤
│ Workspace               │
├─────────────────────────┤
│ [Pilot tabs / bottom]   │  ← nav métier Pilot, pas chrome Core
└─────────────────────────┘
```

---

## Zones topbar (ordre L→R)

| Zone | Contenu | Appartient à |
|------|---------|--------------|
| A | Pilot Mark + wordmark contexte* | Platform (+ teinte si Product) |
| B | App Launcher control | Platform |
| C | Spacer / titre page optionnel | Product (option) |
| D | Global Search | Platform |
| E | Org switcher | Platform |
| F | Notifications | Platform |
| G | Profile | Platform |

\* Sur Product Shell : Mark teinté + nom Pilot + `by ELFIS Core` possible en sidebar plutôt qu’en topbar (voir 08).

**Règle :** A–B–D–E–F–G ne changent **jamais** de place entre Pilot.

---

## Identité visuelle chrome

```
Platform-only surfaces     Product-active surfaces
─────────────────────      ───────────────────────
Topbar fond navy/neutre    Sidebar primary Pilot
Accent #3D7EFF (focus)     Item actif = primary Pilot
Mark navy (si hub)         Mark teinté Pilot
```

---

## Arbre de navigation chrome

```
Platform Shell
├── Launcher ──────────► grille Pilot (+ hub Core si existe)
├── Search ────────────► palette globale
├── Org ───────────────► liste orgs / créer
├── Notifications ─────► centre
└── Profile
    ├── Profil
    ├── Préférences
    ├── Workspace / org
    ├── Admin (droit)
    └── Logout
```

---

## États

| État | Comportement |
|------|--------------|
| Aucun Pilot | Topbar Core ; workspace = hub / empty « Choisir une app » |
| Pilot actif | Product Shell monté sous topbar |
| Overlay ouvert | Focus trap ; Esc ferme ; fond atténué |
| Offline / erreur | Banner sous topbar, chrome reste |

---

## Hors Platform Shell

```
✗ Sidebar métier
✗ Modules CRM / finance
✗ Couleur primary Pilot sur toute la topbar (contamination)
```
