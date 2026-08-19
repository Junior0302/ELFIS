# ELFIS App Launcher V1 (E1.5)

## 1. Vision

**ELFIS Core** est la plateforme mère. Les **Pilot** sont des applications de la suite.

Le Launcher permet de comprendre l’écosystème, identifier l’application active, et découvrir les prochaines apps — sans promettre des produits non lancés.

## 2. Plateforme vs application

| | |
|---|---|
| ELFIS Core | Plateforme (header Launcher) |
| ComptaPilot | Application active V1 |
| SalesPilot / DocPilot | Suite — bientôt disponibles |
| Autres Pilot | Regroupés « À venir » |

## 3. Architecture

```
Product Registry
  → Launcher State Resolver (resolveLauncherProductState / buildLauncherSections)
  → Product Cards
  → Product Selection
  → Overlay closeAll("product_change")
  → Theme update (setCurrentProduct)
  → Route navigation (PRODUCT_ENTRY_ROUTES)
```

Module : `frontend/src/app-launcher/`

## 4. Registry

Source unique `PRODUCT_REGISTRY`. Pas de duplication. `availableInLauncher` + helpers `getLauncherProducts` / `getComingSoonProducts`.

## 5. États produit

`active` · `available` · `beta` · `locked` · `coming_soon` · `unavailable`

Résolus par `resolveLauncherProductState(product, context)` — jamais par la seule couleur.

## 6. Routes

`PRODUCT_ENTRY_ROUTES` — seules les routes SPA réelles :

- `comptapilot` → `/dashboard`
- tous les autres → `null` (non ouvrables)

`websitePath` marketing **interdit** comme route d’app.

## 7. Changement de produit

```
validate → closeAll("product_change") → setCurrentProduct → navigate
```

Si `setCurrentProduct` refuse : pas de navigation, message sûr, ComptaPilot reste.

## 8. Overlays

Desktop : `Popover` (floating). Mobile : `Drawer` bottom.  
Logout / org change / route : intégrations Overlay existantes.  
`closeOnRouteChange` via OverlayRouteBridge.

## 9–10. Desktop / Mobile

Breakpoint aligné shell : `max-width: 1024px`.  
Popover ~440px, scroll interne. Drawer bottom mobile.

## 11. Accessibilité

Trigger `aria-expanded` / `aria-haspopup` / label « Applications ».  
Coming soon : non interactif, badge textuel « Bientôt disponible ».  
Focus / Escape via Overlay System.

## 12–13. Branding / Theming

`ProductMark` : logoMark → fallback initiale + accent produit.  
Panneau : surfaces neutres + en-tête plateforme (bleu nuit discret).  
Cartes : accent par produit via token CSS local. Topbar ComptaPilot inchangée.

## 14–15. Coming soon / Locked

Sales + Doc = cartes featured. Autres = chips.  
`locked` prêt (entitlements contextuels) — non simulé en prod sans source de vérité.

## 16. Analytics

Buffer `productEvents.ts` : `app_launcher.opened|closed|product_selected|coming_soon_viewed`.  
Payload minimal, non bloquant.

## 17. Sandbox

`/dev/design-system/themes` — section App Launcher.  
Preview overrides isolés — **registry jamais muté**.

## 18. Ajouter une application

1. Entrée registry + statut  
2. Route réelle dans `PRODUCT_ENTRY_ROUTES`  
3. `availableInLauncher` seulement si ouvrable  
4. Thème / branding  
5. Tests resolver + launcher  

## 19. Anti-patterns

- Routes fictives `/sales`, `/docpilot`  
- Muter le registry pour la sandbox  
- Portal / Escape maison  
- Bouton coming_soon qui navigue  
- HEX hardcodés dans la logique métier  

## 20. Roadmap V2

Entitlements produit backend · packs · App Launcher Home · deep links multi-shell · Global Search / AI (hors scope).

## Source de vérité V1

Disponibilité = **registry frontend + routes SPA**.  
Pas de nouvelle API. Abonnements Stripe non modifiés.

## Confirmation

**E1.6 n’a pas commencé.**
