# 06 — Autosave UX

## Mécanisme (existant, poli)

| État | Libellé UI |
|------|------------|
| saving | Enregistrement… |
| saved | Sauvegardé — {relatif} |
| error | Erreur — {message} + **Nouvelle tentative** |
| idle | (pas d’indicateur) |

- Autosave silencieux : debounce **2500 ms**, uniquement si `createdDocId` présent.
- Premier enregistrement : action manuelle Brouillon / Enregistrer.
- Post-update réussi → debounce PDF refresh (700 ms).

Pas de nouvel endpoint.
