# ELFIS Design System — Theme Engine Foundation V1 (E1.2)

## 1. Rôle

Le Theme Engine résout un `ProductTheme` depuis le Product Registry, génère des tokens sémantiques, les injecte en variables CSS `--pilot-*`, et les expose à React — **sans migrer les composants métier**.

## 2. Flux

```
ProductIdentity
→ Palette / AccentGradient
→ buildPilotTokens()
→ ProductTheme
→ ProductThemeProvider / createThemeEngine
→ CSS Variables (--pilot-*) + data-* attributes
→ Components (consommation différée à E1.3+)
```

## 3. API publique

Import depuis `frontend/src/design-system` :

| Export | Rôle |
|---|---|
| `resolveProductTheme` | Resolver pur |
| `validateProductTheme` | Validation runtime |
| `themeToCssVariables` | Map tokens → CSS vars |
| `applyProductTheme` / `clearProductTheme` | Injection DOM |
| `ProductThemeProvider` / `useProductTheme` | React |
| `createThemeEngine` | Contrôleur pur (tests / non-React) |
| `PILOT_CSS_VAR_NAMES` / `PILOT_CSS_VAR_BY_TOKEN` | Noms CSS centralisés |
| `getThemeBrandingAsset` | Branding runtime (sans side-effect favicon) |
| `PRODUCT_THEME_STORAGE_KEY` | Persistance |

## 4. Tokens sémantiques

`PilotTokens` (camelCase) : `primary`, `primaryHover`, `primaryActive`, `primaryContrast`, `secondary`, `accent`, `accentSoft`, `surface*`, `border*`, `text*`, `focus`, `success`/`warning`/`danger`/`info`, `chart1`…`chart8`, `gradientStart`/`gradientEnd`.

CSS (source unique `themes/cssVariables.ts`) : `--pilot-primary`, `--pilot-primary-hover`, `--pilot-focus`, `--pilot-chart-1`, …

Les variables legacy (`--forest`, `--mint`, `--ink`, …) **ne sont pas touchées**.

## 5. Provider

```tsx
<ProductThemeProvider initialProductId="comptapilot" allowPreviewUnavailableProducts={false}>
  {children}
</ProductThemeProvider>
```

Monté dans `App.tsx` (racine). Injection `--pilot-*` sur `documentElement` — **aucun composant métier ne les consomme encore** → aucun changement visuel.

## 6. Persistance

- Clé : `elfis.design-system.current-product`
- Stocke uniquement l’ID stable
- Valeur invalide / `coming_soon` / `archived` → ignorée → fallback ComptaPilot

## 7. Fallback

1. `initialProductId` prop  
2. ID persisté valide  
3. Fallback workspace : `comptapilot` (plateforme : `elfis-core`)  
4. ID inconnu : jamais de crash ; fallback + warn DEV

## 8. Preview mode

`allowPreviewUnavailableProducts` (défaut `false`) :

- **application** : seulement `active` / `beta`
- **preview** (sandbox) : tous les thèmes registry

Ne jamais activer le preview dans le shell métier.

## 9. Sandbox

- Route DEV : `/dev/design-system/themes`
- Absente en production (`isDesignSystemSandboxEnabled()`)
- Hors navigation utilisateur
- Exemples neutres (`themeSandbox.css` → uniquement `--pilot-*`)
- Provider local `persist={false}` + DOM bridge sur le host sandbox (n’écrase pas durablement le thème app)

## 10. Sécurité / disponibilité

`setCurrentProduct('salespilot')` en mode application → `false` + erreur contextuelle.  
Pas d’activation produit `coming_soon` dans l’app réelle.

## 11. Migration composants (future E1.3+)

Remplacer progressivement `var(--forest)` / classes hardcodées par `var(--pilot-primary)` **écran par écran**, en commençant par les surfaces non critiques. Ne pas big-bang.

## 12. Anti-flash (future)

Aujourd’hui : fallback ComptaPilot + UI legacy inchangée → flash `--pilot-*` invisible.  
Plus tard : script pré-React minimal écrivant l’ID persisté → tokens avant paint, aligné CSP (`setProperty`, pas de `<style>` injecté).

## 13. Ajouter un thème

1. Palette + gradient + identité registry (E1.1.1)  
2. `buildPilotTokens` dérive automatiquement  
3. Prévisualiser dans la sandbox  
4. Tests resolve / validation  
5. **Ne pas** brancher les composants métier

## 14. Interdictions E1.2

- Pas de migration boutons / sidebar / badges / forms / charts  
- Pas de suppression `--forest` / `--mint`  
- Pas d’App Launcher / routes SalesPilot / Stripe  
- Pas de dark mode incomplet  
- Pas d’E1.3

## Événement optionnel

`elfis:product-theme-changed` — `{ previousProductId, currentProductId, themeId }` — frontend only.

## Audit (stratégie retenue)

| Élément | Décision |
|---|---|
| `themes/interfaces.ts` E1.1 | Étendu → `ProductTheme` runtime |
| `buildPilotTokens` | Passe en tokens sémantiques (+ map legacy) |
| Providers racine | `ProductThemeProvider` autour de `BrowserRouter` |
| `main.tsx` `data-theme` clear | Conservé (anti dark legacy) ; engine réécrit `data-theme` produit |
| CSP | Aucune CSP style stricte → `style.setProperty` |
| Conflit `:root` | Namespaces séparés `--pilot-*` vs `--forest` |
| Tests | Vitest node + fake DOM (pas de nouvelle lib) |
