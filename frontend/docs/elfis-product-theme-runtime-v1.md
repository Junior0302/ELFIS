# ELFIS — Product Theme Runtime V1

## Cause historique de l’oscillation vert/bleu

1. `ProductThemeProvider initialProductId="comptapilot"` forçait le vert au mount (ignorait la route `/sales`).
2. `SalesWorkspaceLayout` forçait `salespilot` en `useEffect` → bascule bleue.
3. StrictMode `destroy()` + `clearProductTheme` → flash vers `:root` vert.
4. `applyProductTheme` clear-then-set → micro-flash vert entre les deux.
5. CSS dual `--pilot-*` vs `--forest/--mint` sur surfaces non migrées.

## Architecture corrigée

```
pathname
  → resolveRuntimeProductFromPath
  → RuntimeThemeSync (unique writer runtime)
  → ThemeEngine.setCurrentProduct(…, { persist })
  → applyProductTheme (atomique)
```

### Priorité

1. Route runtime reconnue
2. Produit sélectionné + route valide (via navigation)
3. Persistée au boot **seulement** si route neutre (et jamais pour écraser `/sales`)
4. Fallback `elfis-core` pour pages publiques
5. Jamais `comptapilot` comme fallback universel

### Persistance

- `/sales` → persist `salespilot`
- `/dashboard` → persist `comptapilot`
- `/login` → thème `elfis-core`, **sans** écraser le dernier produit métier
- Sandbox → `persist: false`, provider imbriqué `applyToDom={false}`

### Anti-flicker

- Bootstrap pré-React : `bootstrapRuntimeProductTheme()`
- `destroy()` ne clear plus le DOM root
- Apply atomique (écrit puis retire les clés absentes)

### Logs DEV

```
[ELFIS Theme]
from=comptapilot
to=salespilot
reason=route_change
path=/sales
```

Oscillation : >3 changements / 2s sans changement de route → `console.error`.
