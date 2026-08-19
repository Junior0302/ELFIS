# Financial Dashboard V1 — ELFIS Core

## Objectif

Un tableau de bord financier moderne, temps réel et orienté décision.
Le Dashboard **ne calcule rien lui-même** : toutes les données proviennent du
**Financial Engine**, unique source de vérité des indicateurs financiers.

## Architecture

```
backend/app/financial/
├── __init__.py            # Description du module
├── financial_types.py     # Types normalisés (Kpi, FinancialAlert, TrendPoint…)
├── engine.py              # FinancialEngine : snapshot, KPIs, tendances, séries
├── alerts.py              # Moteur d'alertes normalisées (fonctions pures)
├── health.py              # Financial Health Score 0-100 (barème documenté)
├── cache.py               # Cache TTL par organisation + suivi de changements
├── financial_events.py    # Publication des événements financial.*
├── platform_service.py    # Vue plateforme (Cockpit Admin)
└── api/routes.py          # Endpoints /financial/* et /platform/financial/*
```

### Sources agrégées par le moteur

| Domaine       | Tables                                        | Indicateurs dérivés                       |
|---------------|-----------------------------------------------|-------------------------------------------|
| Banking       | `bank_accounts`, `bank_transactions`          | Trésorerie, dépenses, catégories, anomalies |
| Banking sync  | `elfis_bank_connections`, `elfis_bank_sync_runs` | Fraîcheur de sync, erreurs, échecs 7 j |
| Facturation   | `sales_documents`                             | CA, TVA collectée, impayés, en attente     |
| Fournisseurs  | `invoices`                                    | TVA déductible, documents à traiter        |

### Fin des calculs dupliqués

Avant ce sprint, les mêmes KPIs étaient calculés dans `routers/dashboard.py`,
`services/finance_agent.py` (`_finance_snapshot`) et `services/banking.py`
(`bank_overview`, `cashflow_forecast`). Désormais :

- `finance_agent._finance_snapshot` **délègue** à `FinancialEngine.snapshot_compat()`
  (le chat IA et `/dashboard/pilot` consomment la même vérité) ;
- le frontend n'effectue **aucun** calcul : il affiche les valeurs, tendances et
  séries fournies par l'API.

## Snapshot (agrégats bruts)

`FinancialEngine.snapshot(organization_id)` calcule en une passe :
trésorerie, crédits/débits, dépenses par catégorie, CA (factures non annulées),
TVA collectée/déductible/estimée, impayés (échéance dépassée) vs en attente,
documents à traiter, buckets mensuels/hebdomadaires/annuels, série de trésorerie
reconstituée, prévision 30/60/90 j (formule historique conservée), état des
synchronisations. Le snapshot est mis en cache (voir Performance).

## KPIs standardisés (9)

Tous les KPI partagent exactement le même format (`financial_types.Kpi`) :

```json
{
  "id": "tresorerie", "label": "Trésorerie",
  "value": 12000.0, "unit": "EUR", "format": "currency",
  "status": "ok | warning | critical | neutral",
  "trend": { "direction": "up|down|flat", "delta": 2500.0, "delta_pct": 26.3, "previous": 9500.0 },
  "hint": "Projection 30 j : 20 000 €"
}
```

| id                          | Valeur                                   | Statut                             |
|-----------------------------|-------------------------------------------|-------------------------------------|
| `tresorerie`                | Somme des soldes bancaires               | critical < 1 000 €, warning < 5 000 € |
| `revenus`                   | CA facturé HT (factures non annulées)    | ok si > 0                           |
| `depenses`                  | Décaissements bancaires cumulés          | neutral                             |
| `resultat`                  | Résultat du mois (CA mois − dépenses mois) | warning si négatif                |
| `tva_estimee`               | TVA collectée − TVA déductible           | warning si > 5 000 €                |
| `factures_impayees`         | Nombre (montant en hint)                 | critical si montant > 10 000 €      |
| `factures_en_attente`       | Nombre (montant en hint)                 | neutral                             |
| `documents_a_traiter`       | À vérifier + en cours d'analyse          | warning si > 0                      |
| `synchronisations_bancaires`| Connexions actives (fraîcheur en hint)   | selon fraîcheur (24 h / 7 j / erreur) |

## Tendances

`/financial/trends` retourne trois horizons — `monthly` (12 mois), `weekly`
(12 semaines ISO), `yearly` (3 ans) — chacun avec :

- `points` : `{period, label, revenue, expenses, result}` ;
- `comparison` : période courante vs précédente (`delta`, `delta_pct`, `direction`)
  pour `revenue`, `expenses` et `result`.

## Graphiques

`/financial/charts` fournit des séries prêtes à afficher :

- `revenue_vs_expenses` : barres mensuelles revenus/dépenses (12 mois) ;
- `treasury` : solde reconstitué mois par mois (net flow inversé depuis le solde actuel) ;
- `expense_breakdown` / `categories` : répartition des dépenses par catégorie (montant, %, nombre) ;
- `ca_evolution` : CA mensuel.

Le frontend (SVG pur, sans bibliothèque) ne fait que le rendu.

## Alertes normalisées

`alerts.build_alerts(snapshot)` — fonctions pures, triées par sévérité :

| Code                 | Condition                                        | Sévérité            |
|----------------------|--------------------------------------------------|---------------------|
| `TREASURY_CRITICAL`  | trésorerie < 1 000 € (configurable)              | critical            |
| `TREASURY_LOW`       | trésorerie < 5 000 € (configurable)              | warning             |
| `VAT_HIGH`           | TVA estimée > 5 000 € (configurable)             | warning             |
| `INVOICE_OVERDUE`    | ≥ 1 facture en retard                            | warning / critical > 10 k€ |
| `UNUSUAL_EXPENSE`    | anomalies bancaires détectées                    | info                |
| `SYNC_ERROR`         | connexion bancaire en erreur                     | critical            |
| `SYNC_MISSING`       | aucune sync depuis plus de 7 jours               | warning             |
| `SYNC_NOT_CONFIGURED`| aucune banque connectée (avec données présentes) | info                |
| `DOCUMENTS_PENDING`  | documents fournisseur à traiter                  | info                |

Seuils dans `app/config.py` : `financial_treasury_low_threshold`,
`financial_treasury_critical_threshold`, `financial_vat_high_threshold`.

## Financial Health Score

Note 0-100, barème documenté dans `health.py` (chaque composant est indépendant
et évolutif) :

| Composant       | Poids | Règle                                                       |
|-----------------|-------|-------------------------------------------------------------|
| Trésorerie      | 30    | Autonomie (trésorerie / dépenses mensuelles) ≥ 3 mois = 30  |
| Retards clients | 20    | Impayés / CA : 0 % = 20, ≥ 30 % = 0 (linéaire)              |
| Revenus         | 20    | Évolution du CA mensuel : ≥ 0 % = 20, ≤ −50 % = 0           |
| Dépenses        | 15    | Dépenses / CA : ≤ 70 % = 15, ≥ 120 % = 0                    |
| Synchronisation | 15    | < 24 h = 15, < 7 j = 8, sinon 0 (sans banque : 5)           |

Grades : A ≥ 80 · B ≥ 65 · C ≥ 50 · D ≥ 35 · E < 35.
Sans donnée : état `setup`, score `null`.

## API

Tous les endpoints acceptent `?refresh=true` (bypass du cache) et exigent un
abonnement actif + organisation :

- `GET /api/financial/overview` — tout le dashboard en un appel
- `GET /api/financial/kpis`
- `GET /api/financial/trends`
- `GET /api/financial/charts`
- `GET /api/financial/alerts`
- `GET /api/financial/health-score`
- `GET /api/platform/financial/overview` — Cockpit Admin (`platform.admin`)

## Frontend

- `frontend/src/services/financialApi.ts` — client typé (+ tests vitest) ;
- `frontend/src/pages/FinancialDashboardPage.tsx` — route `/finance` :
  9 KPI, jauge Health Score, alertes, 4 graphiques SVG, activité récente,
  synchronisations, documents, recommandations. Grilles `auto-fit` → responsive.
  Actualisation automatique toutes les 60 s + bouton « Actualiser » (refresh forcé) ;
- `frontend/src/pages/platform/PlatformFinancePage.tsx` — route `/elfadmin/finance` :
  score moyen, organisations sans synchronisation, alertes, statistiques globales.

## Événements IA

Publiés sur le bus (`financial_events.py`), uniquement **quand les valeurs changent**
(empreinte SHA-256 comparée entre recalculs) :

- `financial.kpi.updated.v1` — les 9 KPIs recalculés ;
- `financial.health.updated.v1` — score, grade, composants ;
- `financial.alert.created.v1` — alerte normalisée (idempotence : 1/jour/code/org).

Ils alimenteront le futur AI Financial Assistant.

## Performance

- Cache TTL par organisation (`cache.KeyedTtlCache`), TTL configurable via
  `financial_cache_ttl_seconds` (défaut 60 s) ;
- `?refresh=true` force le recalcul ; `FinancialEngine.invalidate(org_id)` disponible ;
- le frontend s'actualise automatiquement (60 s), le backend absorbe la charge grâce au cache.

## Tests

`backend/tests/financial/` (54 tests) : calculs du snapshot, homogénéité et valeurs
des KPIs, tendances (3 horizons + comparaisons), toutes les règles d'alertes,
bornes et composants du Health Score, comportement du cache (hit, refresh,
invalidation, TTL), 7 endpoints API, publication des événements (changement
uniquement), isolation par organisation, compatibilité `finance_agent`.

Frontend : `financialApi.test.ts` (6 tests) — parsing, refresh, erreurs, formatage.
