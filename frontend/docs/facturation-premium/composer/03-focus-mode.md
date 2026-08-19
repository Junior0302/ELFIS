# 03 — Focus Mode

## Comportement

Pendant `/facturation/nouveau` (**Full Focus** F1.3.1.1) :

- Nav secondaire Facturation **masquée** (`FacturationLayout` + `hidden`)
- Sidebar produit Compta **masquée** (`WorkspaceLayout` / `isComposerFullFocusPath`)
- Guide Banner + SubscriptionBanner masqués
- `ComposerFocusLayout` : header Focus + workspace éditeur/aperçu plein viewport
- Progression + composer + aperçu + actions visibles
- Sorties : Documents (confirm dirty), Ouvrir doc / Créer autre après création
- PlatformTopbar conservé (hamburger ELFIS, Apps, org, profil, notifs)

## Hook

`useComposerFocus({ exitTargets, onExitNavigate })` — générique.

Flags : `hideSecondaryNav`, `hideProductSidebar`, `hideChromeExtras`.

## Shell

PlatformShell non forké. Classe `ps-shell--composer-focus` + absence de sidebar. Body `data-fp-full-focus`.

Docs UX review : `ux-review/11`–`16`.
