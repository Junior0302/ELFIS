# 04 — Modal Composer refresh

## URL

`/facturation/documents/new?type=invoice` — nested sous Documents.

## Comportement attendu au F5

1. Bootstrap auth + subscription **sans** redirect Home.
2. `FacturationDocumentsPage` monte Documents (`FacturationPage`) + `<Outlet />`.
3. `DocumentCreateFlow` hydrate depuis `useMatch('/facturation/documents/new')` + `?type=` → stage composer.
4. Pas de `backgroundLocation` RR obligatoire : le parent Documents **est** le background (nested route).

## Non-régressions

- `closeOnRouteChange: false` sur le root modal (OverlayRouteBridge ne ferme pas).
- Pas de fermeture silencieuse / bounce Home.
