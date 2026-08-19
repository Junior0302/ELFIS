# Repair — Dashboard client ComptaPilot (version actuelle)

Date : 2026-07-26  
Statut : **restauré** + **surfaces client migrées** (Cockpit inclus)

## Première connexion sans abonnement (2026-07-26)

### Cause

`DashboardPage` appelait `financialApi.overview` **avant** de vérifier l’entitlement.  
`require_active_subscription` renvoyait **402** → message brut « Erreur API 402 ».

### Correction

1. Statut via `resolveCommercialStatus` / `hasFinancialEntitlement` (`SubscriptionInfo.access_granted`).
2. Sans accès : **aucun** appel `/api/financial/overview` → `TrialActivationState`.
3. `apiErrors.ts` : messages UX (401/402/403/404/429/5xx) + logs techniques.
4. Guide dual Accueil (`guide` / `guideLocked`) dans `PageGuide`.
5. Bandeau : CTA « Démarrer mon essai gratuit » si checkout nécessaire.

### États

| Statut | UI |
|--------|-----|
| none / trial_available | Bienvenue + CTA essai |
| checkout_pending | Finaliser souscription |
| expired / suspended / blocked | Message adapté + CTA abo |
| trialing / active / grace (access_granted) | Dashboard Financial Engine complet |



La route `/dashboard` rendait `DashboardPage.tsx`, qui chargeait encore les **anciens** endpoints :

| Ancien appel | Endpoint | Rôle |
|--------------|----------|------|
| `api.dashboard()` | `GET /api/dashboard/stats` | Comptes de factures fournisseur (`Invoice`) |
| `api.dashboardPilot()` | `GET /api/dashboard/pilot` | KPIs via `pilot_kpis` / snapshot compat |

La page **certifiée** Financial Dashboard V1 vit sur `/finance` (`FinancialDashboardPage` → `financialApi.overview` → `/api/financial/overview`).

Le client voyait donc une **UI d’accueil legacy** sans trésorerie, Health Score, alertes normalisées, sync bancaire, ni liens `/finance` / `/banque` / `/copilote`.

Cause : mauvais composant + mauvaise API sur `/dashboard` — pas un cache Vite ni un feature flag.

## Audit routage

| Route | Composant | Fichier |
|-------|-----------|---------|
| `/dashboard` | `DashboardPage` | `frontend/src/pages/DashboardPage.tsx` |
| `/finance` | `FinancialDashboardPage` | `frontend/src/pages/FinancialDashboardPage.tsx` |
| `/banque` | `BankingPage` | `frontend/src/pages/BankingPage.tsx` |
| `/copilote` | `CopilotePage` | `frontend/src/pages/CopilotePage.tsx` |
| `/cockpit` | `CockpitPage` | `frontend/src/pages/CockpitPage.tsx` |
| `/elfadmin/finance` | `PlatformFinancePage` | admin plateforme |

## Statut de `/cockpit`

### Utilité réelle

Surface **ops distincte** (pas un second accueil) :

| Widget | Source | Unique vs Accueil/Finance |
|--------|--------|---------------------------|
| Notifications non lues | SyncProvider | Oui |
| Migrations actives | `migrationApi` | Oui |
| Propositions comptables à revoir | `listAccountingProposals` | Oui |
| Documents à traiter | Financial Engine `documents_to_process` | Aligné Accueil |
| Trésorerie / CA / impayés / Health / alertes | Financial Engine overview | Même vérité qu’Accueil |

### Décision

**A — Conserver** `/cockpit` (utilité ops distincte).  
Ne pas fusionner avec `/dashboard`. Ne pas supprimer.  
Indicateurs financiers raccordés à `financialApi.overview`.

## Ancienne vs nouvelle source

| Surface | Avant | Après |
|---------|-------|-------|
| `/dashboard` | `/dashboard/stats` + `/dashboard/pilot` | `/api/financial/overview` |
| `/cockpit` | `/dashboard/stats` (+ ops APIs) | `/api/financial/overview` (+ ops APIs) |
| `/finance` | Financial Engine | inchangé |

Aucun calcul métier frontend — mapping `dashboardHome.ts` / `extractCanonicalFinancialFacts`.

## Inventaire APIs legacy

| Symbole / route | Classification | Action |
|-----------------|----------------|--------|
| `api.dashboard` | code mort FE | **retiré** |
| `api.dashboardPilot` | code mort FE | **retiré** |
| Types `DashboardStats` / `PilotOverview` | typage legacy | `@deprecated` |
| `GET /api/dashboard/stats` | legacy backend | **deprecated** |
| `GET /api/dashboard/pilot` | legacy backend | **deprecated** |
| `GET /api/platform/dashboard` | actif plateforme | hors scope |
| `smartMigrationApi.dashboard` | actif migration | hors scope |

### Plan de dépréciation

1. FE : méthodes `api.dashboard*` retirées.
2. BE : `deprecated=True` + headers `Deprecation` / `Sunset` (2026-08-01) / `Link` → `/api/financial/overview`.
3. Suppression hard : major suivante après audit usages externes.

## Preuve d’absence de calculs concurrents

- Accueil et Cockpit : uniquement `financialApi.overview`.
- Test `clientFinancialSurfaces.test.ts` : mêmes trésorerie, CA, impayés, Health Score, alertes pour un même overview.
- Aucun appel FE à `/dashboard/stats` ou `/dashboard/pilot`.

## Principes conservés

- `/dashboard` = synthèse + actions  
- `/finance` = analyse détaillée  
- `/cockpit` = ops + rappel santé financière (même Engine)

## Doublons restants (non rationalisés)

| Entrée A | Entrée B | Note |
|----------|----------|------|
| Accueil `/dashboard` | Finance `/finance` | Volontaire |
| Accueil `/dashboard` | Cockpit `/cockpit` | Volontaire (synthèse vs ops) |
| Copilote `/copilote` | Intelligence `/intelligence` | Dual chat — ultérieur |

## Fichiers (cumul migration)

- `frontend/src/pages/DashboardPage.tsx`, `CockpitPage.tsx`, `ReportsPage.tsx`
- `frontend/src/dashboardHome.ts` (+ tests), `clientFinancialSurfaces.test.ts`
- `frontend/src/api.ts`, `navConfig.ts`, `buildInfo.ts`, `main.tsx`, `vite.config.ts`
- `backend/app/routers/dashboard.py`
- `backend/tests/financial/test_legacy_dashboard_deprecated.py`
- `frontend/docs/dashboard-current-version-repair.md`
