# 23 — Modal Composer Changelog

## F1.3.1.3

- **Fix régression** : `OverlayRouteBridge` fermait le dialog sur `navigate(/documents/new)` (`route_change`).
- `DocumentCreationModalRoot` : `closeOnRouteChange: false` + ignore `route_change`.
- State machine unique `ComposerModalStage` (`composerModalMachine.ts`).
- Transition type→composer = `ENTER_COMPOSER` seulement (overlay continu).
- Suppress redirects auto Composer vide / sans type (message in-modal / in-page).
- Tests MM01–40 avec OverlayRouteBridge ; docs 24–31.

## F1.3.1.2

- Remplace la navigation page `/facturation/nouveau` (Full Focus shell) par un **modal Composer** au-dessus de Documents.
- Route nominale : `/facturation/documents/new?type=…` (nested).
- Legacy `/facturation/nouveau` → redirect vers `documents/new`.
- `DocumentCreateFlow` : STATE 1 type + STATE 2 composer, même overlay (bridge anti-flash).
- Confirm sortie : Continuer / Quitter / Enregistrer et fermer.
- Post-création enrichi (Envoyer).
- Shell `isComposerFullFocusPath` désactivé pour le flux nominal.
