# Certification — Financial Dashboard V1

Sprint : Financial Dashboard V1 pour ELFIS Core.
Référence : `docs/financial/financial-dashboard-v1.md`.

## Critères de certification

### ✔ Financial Engine unique source de vérité

- `backend/app/financial/engine.py` centralise **tous** les calculs financiers
  (trésorerie, CA, dépenses, bénéfice, TVA estimée, résultat mensuel, marge, évolution).
- Les calculs auparavant dupliqués dans `finance_agent._finance_snapshot` sont
  supprimés : la fonction délègue à `FinancialEngine.snapshot_compat()` — le chat IA
  et `/dashboard/pilot` consomment le même moteur.
- Le frontend n'effectue aucun calcul : `financialApi.ts` ne fait que du fetch,
  les composants SVG ne font que du rendu de séries.
- Vérifié par `tests/financial/test_financial_engine.py::test_finance_agent_delegates_to_engine`.

### ✔ KPIs homogènes

- 9 indicateurs standardisés (`tresorerie`, `revenus`, `depenses`, `resultat`,
  `tva_estimee`, `factures_impayees`, `factures_en_attente`, `documents_a_traiter`,
  `synchronisations_bancaires`).
- Format unique `Kpi` (Pydantic, `extra="forbid"`) : id, label, value, unit, format,
  status, trend (direction/delta/delta_pct/previous), hint.
- Vérifié par `test_financial_kpis.py::test_kpis_are_homogeneous`.

### ✔ API cohérentes

- `GET /financial/overview | /kpis | /trends | /charts | /alerts | /health-score`
  + `GET /platform/financial/overview` (admin).
- Convention commune : abonnement actif requis, organisation obligatoire,
  paramètre `?refresh=true` sur tous les endpoints de calcul.
- Vérifié par `test_financial_api.py` (8 tests, 7 endpoints).

### ✔ Dashboard responsive

- `frontend/src/pages/FinancialDashboardPage.tsx` (route `/finance`) :
  KPI principaux, 4 graphiques (revenus vs dépenses, trésorerie, évolution CA,
  répartition des dépenses), alertes, activité récente, Health Score,
  synchronisations, documents.
- Grilles CSS `repeat(auto-fit, minmax(...))` et SVG `viewBox` fluides → mobile/desktop.
- Actualisation automatique toutes les 60 s + rafraîchissement manuel forcé.

### ✔ Alertes

- Moteur d'alertes normalisées (`app/financial/alerts.py`) : trésorerie
  faible/critique, TVA importante, factures impayées, dépenses inhabituelles,
  synchronisation absente/en erreur, documents en attente.
- Format unique `FinancialAlert` (code stable, sévérité, titre, message, action).
- Seuils configurables. Vérifié par `test_financial_alerts.py` (9 tests).

### ✔ Health Score

- Score 0-100 (`app/financial/health.py`), barème documenté et évolutif :
  Trésorerie 30 · Retards 20 · Revenus 20 · Dépenses 15 · Synchronisation 15.
- Grades A-E, état `setup` sans données, composants détaillés exposés à l'API
  et affichés dans le dashboard (jauge + barres).
- Vérifié par `test_financial_health.py` (5 tests).

### ✔ Documentation

- `docs/financial/financial-dashboard-v1.md` (architecture, KPIs, alertes,
  barème du score, API, cache, événements).
- `frontend/docs/financial-dashboard-v1-certification.md` (ce document).

### ✔ Tests verts

Backend — `python -m pytest tests/financial -q` :

```
54 passed
```

Combinés (non-régression) — `python -m pytest tests/events tests/financial tests/banking -q` :

```
101 passed
```

Frontend — `npx tsc -b` : 0 erreur · `npm test` :

```
Test Files  18 passed (18)
Tests       64 passed (64)
```

Note : un correctif de cause racine a été apporté à
`app/document_intake/models.py` (import du modèle `elfis_migration_sessions`
référencé par FK), ce qui répare aussi 12 échecs préexistants de `tests/events`
en exécution combinée.

## Événements IA (bonus mission)

`financial.kpi.updated.v1`, `financial.health.updated.v1`,
`financial.alert.created.v1` — publiés uniquement quand les valeurs changent
(empreintes comparées), idempotence par jour pour les alertes.
Vérifié par `test_financial_events.py` (4 tests).

## Performance

Cache TTL par organisation (60 s configurable), invalidation ciblée,
actualisation automatique côté frontend absorbée par le cache.
Vérifié par `test_financial_cache.py` (7 tests).

## Verdict

**FINANCIAL DASHBOARD V1 CERTIFIED**
