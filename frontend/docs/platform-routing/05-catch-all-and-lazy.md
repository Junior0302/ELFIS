# 05 — Catch-all & lazy

## Avant

```tsx
<Route path="*" element={<Navigate to="/" replace />} />
```

Risque : 404 / mismatch → Landing ; confusion avec bounce Home.

## Après

- `path="*"` → `RouteNotFound` (Accueil / Dashboard en liens, **pas** redirect auto).
- `Suspense` → `BootstrapLoadingScreen` (wait, pas Home).
- `RouteChunkErrorBoundary` → Réessayer / Accueil sur erreur de chunk.

Les routes lazy déclarées restent matchées avant le catch-all ; Suspense ne bascule pas sur `*`.
