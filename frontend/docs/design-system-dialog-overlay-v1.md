# ELFIS Design System — Dialog & Overlay System V1 (E1.4.1)

## Overlay Orchestration

### Rôle

`OverlayProvider` embarque un **Overlay Manager** (`createOverlayManager`) — point de coordination unique pour Dialog, ConfirmDialog, Drawer, Popover, Tooltip.

Les composants restent **controlled** (`open` / `onOpenChange`). Le manager n’est pas un moteur de rendu impératif.

```
useOverlayBehaviour → registerOverlay(descriptor)
OverlayProvider     → Escape unique, scroll lock dérivé, Portal root
closeAllOverlays()  → bridge logout / org (auth.tsx)
OverlayRouteBridge  → route_change
```

### API publique — `useOverlayManager()`

- `registerOverlay` / `updateOverlay` / `unregisterOverlay`
- `requestClose(id, reason?)` / `closeTop` / `closeAll`
- `isOpen` / `isTopOverlay` / `getTopOverlay` / `getStack` / `getStackDepth`

Pas de mutation libre de la stack.

### Priorités

| Type | Priorité |
|---|---|
| tooltip | passive |
| popover | floating |
| drawer non modal | panel |
| drawer modal / dialog / confirm | modal |
| critical_dialog | critical |

À priorité égale : plus récent = top. Enfant (`parentOverlayId`) au-dessus du parent même si priorité inférieure.

### Fermeture — `OverlayCloseReason`

`escape` · `backdrop` · `action` · `cancel` · `route_change` · `logout` · `organization_change` · `product_change` · `provider_unmount` · `programmatic` · `parent_closed`

- Escape / backdrop : top overlay dismissible seulement
- Force (ignore `dismissible=false`) : logout, org, product, provider_unmount, parent_closed, programmatic, route_change
- Fermeture parent → enfants en `parent_closed` (pas d’orphelins)
- `closeAll` : ordre inverse, un seul cycle de restore focus (`isBulkClosing`)

### Lifecycle branché

| Événement | Action |
|---|---|
| Logout réussi | `closeAllOverlays('logout')` dans `auth.tsx` |
| Changement d’org (`setOrgId`) | `closeAllOverlays('organization_change')` |
| Changement de route | `OverlayRouteBridge` → `requestClose(..., 'route_change')` si `closeOnRouteChange` |
| Changement de produit App Launcher | **Non branché** — utiliser `closeAll('product_change')` ; ne pas lier à la sandbox thème |

### Focus

Top overlay seul piège le focus. Enfant fermé → parent si encore ouvert. `closeAll` → pas de multi-sauts. Fallback : trigger → parent → body.

### Scroll lock

Compteur dérivé de `lockScroll` sur la stack (OverlayProvider). Plus de locks indépendants non coordonnés.

### Événements frontend

`elfis:overlay-opened` · `elfis:overlay-closed` · `elfis:overlay-stack-changed`  
Payload : `overlayId`, `overlayType`, `priority`, `stackDepth`, `reason?` — jamais de contenu métier / PII.

### Futurs modules (interdiction d’infra parallèle)

AI Assistant, Global Search, Command Palette, Notification Center, App Launcher, wizards, assistants Pilot : **composer** Dialog/Drawer/Popover via OverlayProvider — ne pas créer Portal / Escape / scroll lock / z-index maison.

### API impérative future (documentée, non construite)

```ts
// Futur — hors E1.4.1
overlay.open(...)
overlay.confirm(...) // Promise
```

V1 = instances controlled + orchestration.

### Anti-patterns

- Portal métier hors OverlayProvider
- `z-index: 999999`
- Listener Escape global parallèle
- `document.body.overflow` manuel
- Overlay survivant à un changement d’organisation

---


```
App
 └─ OverlayProvider          # stack + #elfis-overlay-root (créé dès le 1er render)
     └─ Portal               # createPortal → root dédié (fallback body)
         ├─ Dialog / ConfirmDialog
         └─ Drawer
 Tooltip / Popover           # positionnement CSS local (hors Portal, Option B)
```

Indépendant du métier : pas de fetch, routes, permissions, Product Registry ni texte métier.

## 2. OverlayProvider

API : `registerOverlay`, `unregisterOverlay`, `getTopOverlay`, `isTopOverlay`, `portalRoot`, `stackDepth`.

Le root `#elfis-overlay-root` est créé de façon synchrone pour éviter un basculement body → root (perte de focus).

## 3. Portal

- Conteneur dédié `#elfis-overlay-root`
- Fallback `document.body`
- Sûr sans `document` (SSR / node)
- Pas de `dangerouslySetInnerHTML`

## 4. Z-index

| Token | Usage |
|---|---|
| `--z-base` | Contenu page |
| `--z-sticky` | Headers sticky |
| `--z-dropdown` | Menus legacy |
| `--z-popover` | Popover |
| `--z-tooltip` | Tooltip |
| `--z-drawer` | Drawer |
| `--z-dialog` | Dialog / Confirm |
| `--z-critical-overlay` | Bloquants critiques |

Hiérarchie : base < sticky < dropdown < popover < tooltip < drawer < dialog < critical.

## 5. Focus management

Helpers : `getFocusableElements`, `focusFirstElement`, `focusLastElement`, `restoreFocus`, `trapTabKey`.

- Focus initial dans le panel modal
- Tab / Shift+Tab bouclent (top overlay uniquement)
- Escape top-only
- Restauration sur le déclencheur (fallback sûr)
- Confirm danger : focus initial sur Annuler
- Pas de trap sur Tooltip

### Décision `<dialog>` natif

**Non retenu en V1.** Avantages natifs (top layer, focus) vs limites jsdom / contrôle stack Portal unifié. Réévaluation possible plus tard.

## 6. Scroll lock

Compteur de référence + compensation scrollbar (`padding-right` si gap réaliste). Dialog / Drawer modal uniquement. Tooltip / Popover non modal : pas de lock.

## 7–11. Composants

| Composant | Rôle |
|---|---|
| **Dialog** | Modal générique (`role="dialog"`, `aria-modal`) |
| **ConfirmDialog** | Remplace `window.confirm` (tones, async loading) |
| **Drawer** | left / right / bottom, modal optionnel |
| **Tooltip** | Hover + focus, `aria-describedby` |
| **Popover** | Panneau léger, `modal=false` par défaut |

### Positionnement Tooltip / Popover — Option B

CSS relative/absolute, **sans Floating UI** (dépendance non justifiée pour V1 ; placements top/right/bottom/left).

## 12. Theming

Surfaces neutres ELFIS + `--pilot-primary` pour accents/focus. Danger / warning / success globaux inchangés. Pas de HEX dans les composants.

## 13–15. Accessibility / responsive / nested

- Reduced motion : animations réduites via tokens / `prefers-reduced-motion`
- Dialog lg/xl : quasi plein écran mobile ; contenu scrollable, header/footer stables
- Nested : Escape / focus trap uniquement sur le top overlay

## 16. Migrations pilotes

| # | Surface | Cible | Risque |
|---|---|---|---|
| 1 | `ClientsPage` delete | ConfirmDialog danger | Faible |
| 2 | `HistoryPage` delete | ConfirmDialog danger | Faible |
| 3 | `AuditEventDetailsDrawer` | Drawer | Moyen |

## 17. Matrice legacy

| Surface existante | Type | Problèmes | Cible ELFIS | Migration |
|---|---|---|---|---|
| ClientsPage confirm | `window.confirm` | Native, a11y | ConfirmDialog | **Migré V1** |
| HistoryPage confirm | `window.confirm` | Native | ConfirmDialog | **Migré V1** |
| AuditEventDetailsDrawer | Drawer ad-hoc | Pas trap / scroll lock | Drawer | **Migré V1** |
| DecisionDetail ConfirmDialog | Modal CSS local | Escape/focus incomplets | ConfirmDialog | Reportée |
| SalesDocPreviewModal | Modal | role sur backdrop | Dialog | Reportée |
| Trial Tour | Dialog spécifique | Spécifique métier | Dialog | Reportée |
| Autres `window.confirm` | Native | — | ConfirmDialog | Reportée |
| Platform legal hold | Modal | Minimal | Dialog | Reportée |
| ProcessingJobDetailsDrawer | Aside | Non modal | Drawer | Reportée |
| Z-index 9999 dispersés | CSS | Conflits | Tokens `--z-*` | Partiel (nouveaux) |

## 18. Règles d’usage

1. Toujours sous `OverlayProvider` (monté dans `App`)
2. Imports depuis `design-system` (pas d’imports profonds)
3. Confirm danger → focus Annuler
4. Pas d’info essentielle uniquement dans Tooltip
5. Popover non modal par défaut
6. Libellés fournis par l’appelant

## 19. Anti-patterns

- `z-index: 9999` ad-hoc
- Fetch / permissions dans overlays DS
- Plusieurs listeners Escape globaux
- Div cliquable sans bouton
- Floating UI maison complexe

## 20. Reportés (hors E1.4.1)

Dropdown/Menu, Context Menu, Command Palette, Toast System, DatePicker, Calendar, Combobox, FilePicker, Tour guidé générique, **E1.5**.

## Testing Library / jsdom

Ajoutés et utilisés :

- `jsdom`
- `@testing-library/react`
- `@testing-library/user-event`
- `@testing-library/jest-dom`

Vitest : `*.test.tsx` + `setupFiles` jest-dom. Les overlays ne se contentent plus de `renderToStaticMarkup`.

## Exemples

```tsx
<Dialog open={open} onOpenChange={setOpen} title="Titre" description="…">
  Contenu
</Dialog>

<ConfirmDialog
  open={open}
  onOpenChange={setOpen}
  title="Supprimer ?"
  description="Irréversible"
  tone="danger"
  onConfirm={async () => { await api.delete(id) }}
/>

<Drawer open={open} onOpenChange={setOpen} side="right" title="Détail">
  …
</Drawer>

<Tooltip content="Aide"><button type="button">?</button></Tooltip>

<Popover open={open} onOpenChange={setOpen} trigger={<button>Plus</button>}>
  Actions simples
</Popover>
```

## Sandbox

`/dev/design-system/themes` — section **Overlay System V1** (Dialog, Confirm ×3, Drawer, Tooltip, Popover, nested, scroll long). Accents Pilot via sélecteur ComptaPilot / SalesPilot / DocPilot.

## Confirmation

**E1.5 n’a pas commencé.**
