# ELFIS Design System — Product Identity V1 (E1.1.1)

## 1. Philosophie ELFIS Core → Pilot

```
ELFIS Core (plateforme)
        ↓
   Pilot (application métier)
        ↓
 Composants / tokens / UX partagés
```

ELFIS Core est la plateforme mère. Les Pilots (ComptaPilot, SalesPilot, …) sont des applications métier qui partagent composants, animations, layouts et règles UX. Seule l’identité visuelle change par Pilot.

**E1.1.1 enrichit la fondation** (identité, catégories, helpers) sans Theme Engine ni injection CSS.

## 2. Plateforme vs application

| Famille (`productFamily`) | Rôle | Exemple |
|---|---|---|
| `platform` | Socle compte / org / sécurité / services | ELFIS Core |
| `pilot_app` | Application utilisateur métier | ComptaPilot |
| `shared_service` | Brique technique (hors launcher public) | Vault, Decision Center — non déclarés ici |
| `future_product` | Réservé | — |

Les services partagés (Vault, Decision Center, Work Queue) ne sont **pas** des applications Product Launcher.

## 3. ProductIdentity

Source unique : `frontend/src/design-system/products/registry.ts`.

Contrat principal : `ProductIdentity` (`types/index.ts`).

Champs clés :

- Identifiants stables : `id`, `slug` (jamais le `displayName`)
- Famille / catégorie : `productFamily`, `category`
- Copy : `tagline`, `shortDescription`, `longDescription?`
- Statut : `active` \| `beta` \| `coming_soon` \| `internal` \| `archived`
- Thème futur : `themeId` (V1 = égal à `id`)
- Branding paths : `logo`, `logoMark`, `favicon` (+ `branding.*`)
- Marketing : `accentGradient`, `marketingColor`, `illustrationStyle`
- Surfaces : `websitePath`, `documentationPath`, `launchOrder`, `availableInLauncher`
- Commercial (préparation) : `availableForSubscription`, `standaloneEligible`, `bundleEligible`, `pricingModel`

Alias historique : `ProductDefinition` = `ProductIdentity`.

### Écarts vs registry E1.1

| E1.1 | E1.1.1 |
|---|---|
| `name` / `description` | `displayName` / `shortDescription` (+ `tagline`) |
| Statuts `active\|beta\|coming_soon` | + `internal\|archived` |
| Branding `/branding/{id}/` | `/branding/products/{id}/` (+ `logo-mark`, `illustrations/`) |
| Pas de famille / catégorie | `productFamily`, `category` |
| Pas de flags commerciaux | `pricingModel`, eligibility flags |
| Helpers limités | helpers launcher / abonnements / catégories |

**Convention d’ID** : kebab-case (`elfis-core`), stable depuis E1.1. Les exemples underscore du brief (`elfis_core`) ne sont pas adoptés pour ne pas casser la source unique.

## 4. Catégories

Source : `products/categories.ts`.

| id | Label |
|---|---|
| platform | Plateforme |
| finance | Finance et comptabilité |
| sales | Ventes et relation client |
| documents | Documents et connaissance |
| people | Ressources humaines |
| legal | Juridique et conformité |
| operations | Opérations et logistique |
| marketing | Marketing et croissance |
| projects | Projets et collaboration |
| support | Support et service client |

Mapping produit → catégorie : **uniquement** dans le registry (pas dans les composants).

## 5. Statuts

- `active` — utilisable
- `beta` — utilisable, signalé beta
- `coming_soon` — déclaré, non exposé launcher / abonnement
- `internal` — hors surfaces publiques
- `archived` — retiré

Déclaration V1 : ELFIS Core + ComptaPilot `active` ; autres Pilots `coming_soon`.

## 6. Branding paths

Convention :

```
/branding/products/<product-id>/logo.svg
/branding/products/<product-id>/logo-mark.svg
/branding/products/<product-id>/favicon.svg
/branding/products/<product-id>/illustrations/
```

Dossiers sous `public/branding/products/<id>/` avec README placeholder. **Aucun logo définitif.**

## 7. Abonnements / bundles (préparation)

Aucun prix, aucun Stripe, aucun pack.

| Produit | pricingModel | Notes |
|---|---|---|
| ELFIS Core | `included` | Jamais vendu standalone |
| ComptaPilot | `standalone_and_bundle` | `availableForSubscription: true` |
| Autres Pilots | `standalone_and_bundle` | `availableForSubscription: false` tant que `coming_soon` |

## 8. Exemples

```ts
import {
  getProductById,
  getProductsByCategory,
  getLauncherProducts,
  isProductAvailable,
  validateProductRegistry,
} from '@/design-system'

getProductById('comptapilot').category // 'finance'
getProductsByCategory('sales') // [SalesPilot]
getLauncherProducts() // ELFIS Core + ComptaPilot
isProductAvailable('salespilot') // false
validateProductRegistry().ok // true
```

## 9. Comment ajouter une nouvelle application ELFIS

1. Ajouter l’`id` dans `ProductId` (`types/index.ts`).
2. Ajouter la palette dans `colors/palettes.ts`.
3. Ajouter le gradient dans `colors/gradients.ts`.
4. Créer l’entrée `defineProduct(...)` dans `products/registry.ts` (identité, catégorie, statut, flags).
5. Créer `public/branding/products/<id>/README.md`.
6. Étendre les tests (`design-system.test.ts`).
7. Lancer `validateProductRegistry` (doit rester `ok`).
8. **Ne pas** modifier les composants métier, la sidebar, ni injecter de tokens CSS.

## 10. Interdictions

- Pas de Theme Engine / ThemeProvider
- Pas d’injection de tokens dans `:root` / DOM
- Pas de modification Dashboard / Sidebar / Boutons / ComptaPilot UI
- Pas d’App Launcher, page marketing, routes, Stripe
- Pas d’ajout SalesPilot / DocPilot dans la navigation réelle
- Pas de second registry
- Pas commencer E1.2 dans cette étape

## Helpers

| Helper | Rôle |
|---|---|
| `getProductById` | Identité par id |
| `getProductBySlug` | Identité par slug |
| `getProductsByCategory` | Filtre catégorie |
| `getLauncherProducts` | `availableInLauncher` |
| `getActiveProducts` | `status === active` |
| `getComingSoonProducts` | `status === coming_soon` |
| `getStandaloneProducts` | éligibilité standalone |
| `getBundleEligibleProducts` | `bundleEligible` |
| `getProductCategory` | catégorie du produit |
| `isProductAvailable` | active \| beta |
| `validateProductRegistry` | cohérence globale |
