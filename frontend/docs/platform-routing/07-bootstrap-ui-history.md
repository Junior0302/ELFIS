# 07 — Bootstrap UI & history

## BootstrapLoadingScreen

Une surface unique (`auth-boot` / `data-testid="bootstrap-loading"`) pour auth, subscription, suspense route.

Objectif : **une** transition stable — pas de flash Home ↔ route.

## History / deep links

- Back/forward : URL source de vérité ; layouts + theme suivent le path.
- Deep link direct : même pipeline RequireAuth → ProductAccessLayout → layout Pilot.

## Erreurs load

- Subscription : message + Réessayer / Accueil (lien), **pas** redirect auto.
- Chunk : idem via `RouteChunkErrorBoundary`.
- 404 : `RouteNotFound`.
