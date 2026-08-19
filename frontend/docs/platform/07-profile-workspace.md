# 07 — Profile & Workspace

**P1.1** · Identité utilisateur + contexte organisation / workspace.

---

## Menu profil

```
[Avatar] ▼
    │
    ├─ Nom + email
    ├─ ─────────────
    ├─ Mon profil
    ├─ Préférences
    ├─ Workspaces & organisations
    ├─ Administration (si droit)
    ├─ ─────────────
    └─ Déconnexion
```

---

## Workspace / Org

```
Org switcher (topbar E)     Menu profil → Workspaces
         │                            │
         └──────────┬─────────────────┘
                    ▼
         ┌─────────────────────┐
         │ Organisations       │
         │ ● Acme SAS          │
         │ ○ Beta SARL         │
         │ ─────────────       │
         │ + Créer / rejoindre │
         └─────────────────────┘
```

**Règle :** changer d’org = recharge contexte ; Pilot peut retomber sur hub / dernier Pilot de l’org.

---

## Écrans liés (blueprint)

| Écran | Contenu min |
|-------|-------------|
| Profil | Avatar, nom, email, langue |
| Préférences | Thème clair/sombre*, densité, notifs, raccourcis |
| Workspaces | Liste orgs, rôle, switch |
| Admin org | Membres, rôles, billing (lien) — détail métier hors P1.1 |

\* Thème = préférence user ; **primary Pilot** reste Brand produit.

---

## Arbre

```
Profile domain
├── Identity (user)
├── Preferences
├── Org context
│   ├── Switch
│   ├── Members (admin)
│   └── Settings (admin)
└── Session (logout)
```

---

## Continuité cross-Pilot

```
Persiste                    Ne persiste pas forcément
─────────────────────────   ─────────────────────────
User session                Scroll position Pilot
Org active                  Filtres locaux métier
Préférences UI              Drafts non sauvés
```

---

## Do / Don’t

```
DO                          DON’T
──────────────────────────  ──────────────────────────
Org toujours lisible topbar  Org caché dans Pilot only
Logout clair                Logout noyé
Rôle visible si admin       Menus vides trompeurs
```
