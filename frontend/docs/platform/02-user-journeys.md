# 02 — User Journeys

**P1.1** · Parcours cibles (happy path + branches).

---

## Acteurs

```
Owner / Admin org
Member (métier)
Guest / limited   (hors scope détail P1.1 — noter contraintes)
```

---

## J1 — Première connexion

```
Landing ELFIS
    │
    ▼
Login / SSO
    │
    ▼
[Org?]──non──► Créer / rejoindre org (hors blueprint détail)
    │oui
    ▼
Platform Shell
    │
    ▼
App Launcher (suggestion Pilot)
    │
    ▼
Product Shell (ex. ComptaPilot)
```

**Besoins chrome :** Mark Core · launcher · org · profil.

---

## J2 — Journée de travail mono-Pilot

```
Ouvrir session
    │
    ▼
Topbar (org OK) + Product Shell
    │
    ├── Sidebar métier → listes / détail
    ├── Search (⌘K) → entité Pilot
    └── Notif → deep-link dans le Pilot
```

---

## J3 — Basculer de Pilot (cœur écosystème)

```
SalesPilot (pipeline)
    │
    │  besoin facture / compte
    ▼
App Launcher  ──ou──  Search « Compta… »
    │
    ▼
ComptaPilot
    │
    • Mark teinté change (vert)
    • Wordmark + by ELFIS Core
    • Org / user / notifs IDENTIQUES
    • Sidebar = nav finance
```

```
AVANT                         APRÈS
┌─────────────────────┐       ┌─────────────────────┐
│ ELFIS │ ☰ │ Sales…  │       │ ELFIS │ ☰ │ Compta… │
├───────┴─────────────┤       ├───────┴─────────────┤
│ Sales nav │ board   │  ──►  │ Compta nav │ ledger │
└─────────────────────┘       └─────────────────────┘
```

---

## J4 — Recherche transverse

```
⌘K / bouton Search
    │
    ▼
Palette globale
    ├── Résultats Pilot actif (prioritaires)
    ├── Résultats autres Pilot (groupés)
    ├── Actions (ouvrir launcher, switch org…)
    └── Entités plateforme (membres, settings)
         │
         ▼
Deep-link → Pilot cible + entité
```

---

## J5 — Notification → action

```
Badge notif
    │
    ▼
Centre notifications
    │
    ├── Filtrer: All | Pilot | Platform
    └── Clic item
            │
            ▼
      Route Pilot + focus objet
      (si autre Pilot → switch + toast discret)
```

---

## J6 — Profil / workspace

```
Avatar
    │
    ▼
Menu profil
    ├── Mon profil
    ├── Préférences
    ├── Workspaces / Orgs → switch
    ├── Admin org (si droit)
    └── Déconnexion
```

---

## Matrice parcours × chrome

| Journey | Launcher | Search | Notif | Profil | Switch Pilot |
|---------|----------|--------|-------|--------|--------------|
| J1 | ● | ○ | ○ | ● | ○ |
| J2 | ○ | ● | ● | ○ | ○ |
| J3 | ● | ● | ○ | ○ | ● |
| J4 | ○ | ● | ○ | ○ | ● |
| J5 | ○ | ○ | ● | ○ | ● |
| J6 | ○ | ○ | ○ | ● | ○ |
