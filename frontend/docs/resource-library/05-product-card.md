# 05 — Resource Card (product card)

## Affiché

- Nom, type (badge), prix HT, TVA, statut
- Unité + dernière utilisation (message honnête si `null`)
- Description si présente (clamp 2 lignes)

## Actions

| Action | LocalLibrary | Notes |
|--------|--------------|-------|
| Ajouter | disponible (message → Composer/Picker) | Pas d’ajout ligne hors document |
| Modifier | `capabilities.update` | Formulaire inline |
| Dupliquer | `create` copie | API create |
| Voir | détail modal léger | |
| Historique | **disabled** | Pas d’API |

`getResourceActions(source)` dérive les flags depuis `capabilities`.
