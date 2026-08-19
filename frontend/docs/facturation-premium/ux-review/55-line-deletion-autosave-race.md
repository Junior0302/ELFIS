# 55 — Autosave race (line deletion)

## Problème

Save en vol avec payload stale pendant qu’une suppression locale avance.

## Garde-fous

1. `buildPayload()` lit `draftRef.current` (toujours frais au kick)  
2. `draftEpochRef` incrémenté à chaque mutation products  
3. Réponse API : **uniquement** `createdDocId` / `createdDocNumber` — jamais `products`  
4. Si `epoch` a changé pendant le save → `dirty` reste true + re-schedule silent save (last-write-wins)

## Résultat

Une réponse ancienne ne peut pas « ressusciter » une ligne supprimée dans l’UI.
