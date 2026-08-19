# ELFIS Core — Platform Shell V1

## Modèle

```
ELFIS Core (plateforme)
├── Pages publiques (/ , /login, …) → identité elfis-core
├── PlatformShell (topbar globale)
│   ├── App Launcher
│   ├── Organisation
│   ├── Notifications
│   └── Profil / déconnexion
└── ProductShell
    ├── ComptaPilot (vert) — sidebar finance
    └── SalesPilot (bleu) — sidebar CRM
```

## Règle d’identité

- **ELFIS Core** = plateforme (navy)
- **ComptaPilot** = application finance (vert)
- **SalesPilot** = application ventes (bleu)
- **App Launcher** = composant plateforme, pas un gadget ComptaPilot

## Source de vérité thème

`resolveRuntimeProductFromPath(pathname)` → `RuntimeThemeSync` → Theme Engine.

Les layouts produit **ne doivent pas** appeler `setCurrentProduct` pour l’identité.
