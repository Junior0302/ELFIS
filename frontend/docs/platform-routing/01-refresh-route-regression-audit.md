# 01 — Refresh route regression audit (F1.3.2.3)

## Symptôme

Quel que soit l’écran authentifié, **F5** aboutit à **ELFIS Core Home (`/home`)**.

## Matrice audit (code + scénario mental)

| Route demandée | 1ère redirect (avant fix) | Route finale | Guard responsable |
|----------------|---------------------------|--------------|-------------------|
| `/dashboard` | `/welcome` | `/home` | ProductAccessLayout `no_entitlement` → welcome entitled → `/home` |
| `/facturation/documents` | `/welcome` | `/home` | idem |
| `/facturation/documents/new?type=invoice` | `/welcome` | `/home` | idem (+ perte modal) |
| `/finance` | `/welcome` | `/home` | idem |
| `/accounting/proposals` | `/welcome` | `/home` | idem |
| `/platform/relations` | `/welcome` | `/home` | idem |
| `/platform/documents` | `/welcome` | `/home` | idem |
| `/copilote` (assistant) | `/welcome` | `/home` | idem |
| `/settings` | `/welcome` | `/home` | idem |

## Cause exacte

1. `SubscriptionProvider` initialisait `loading = false` et `subscription = null`.
2. Au premier rendu post-auth (après `RequireAuth`), `resolveProductPhase` voyait `subscriptionLoading: false` + `subscription == null` → **`no_entitlement`**.
3. `ProductAccessLayout` faisait `<Navigate to="/welcome" replace />` (remplace l’URL demandée).
4. L’API subscription répondait ensuite → phase **`entitled`**.
5. Sur `/welcome` entitled : `<Navigate to="/home" replace />`.

**Race F5** : demandée → welcome → home. Le catch-all `*` → `/` (Landing) était un second piège pour routes inconnues / erreurs, mais **pas** la cause principale du bounce Home.

## Redirects inventoriés (grep)

| Pattern | Fichier | Rôle |
|---------|---------|------|
| `Navigate to="/home"` | `ProductAccessLayout` | welcome entitled (corrigé : restore `from`) |
| `Navigate to="/welcome"` | `ProductAccessLayout` | no_entitlement (conserve `state.from`) |
| `path="*"` → `/` | `App.tsx` | **remplacé** par `RouteNotFound` |
| `navigate('/home')` défaut login | `LoginPage` | fallback si pas de `from` |
| `RequireAuth` → `/login` | `RequireAuth` | OK si `from` complet |

## Après correctif

Pendant bootstrap subscription → `BootstrapLoadingScreen` (URL inchangée). Puis outlet de la **route demandée**.
