# 20 — Fermeture & fin de flux modal

## Fermeture

| État | Comportement |
|------|----------------|
| Sans modification | Close immédiat → Documents |
| Autosaved (`createdDocId`, pas dirty) | Close (+ `?doc=` si id) |
| Unsaved / dirty | Confirm : **Continuer** / **Quitter** / **Enregistrer et fermer** |

X / Escape / backdrop : même politique (bloqués si confirm dirty ouvert via `onDismissBlockChange`).

## Post-création

Rester dans le dialog : Ouvrir le document | Envoyer | Revenir aux Documents | Créer un autre.

- **Revenir / Ouvrir** → close + `navigate(?doc=)` + `billingOverview` refresh (pas full reload)
- **Créer un autre** → `/documents?create=1` (STATE 1)
- Focus retour : bouton « Créer un document » (`returnFocusRef`)
