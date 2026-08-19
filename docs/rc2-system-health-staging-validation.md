# Rapport RC2.1 — Validation staging System Health

Date : `2026-07-22T14:24:13.807289+00:00`
Statut final : **PASS**

## Environnement

- ELFIS_ENVIRONMENT : `staging`
- Dialecte : `postgres`
- Hôte (masqué) : `db.***abase.co`
- URL (masquée) : `postgresql+psycopg://postgres:***@db.stckzlalxrupgawgrojk.supabase.co:5432/postgres`
- Flag global USE_REAL_PROVIDERS : `False`

## Providers activés (individuels)

- `api` = **real**
- `postgresql` = **real**
- `jobs_queue` = **real**
- `event_bus` = **real**
- `search` = **real**

## Résultats providers

### api

- status : `healthy`
- latency_ms : `1695.91`
- version : `0.8.9`
- checked_at : `2026-07-22T14:24:16.479448`
- summary : API processus opérationnelle
- error_code : `None`
- métriques :
  - `uptime_seconds` = `0.0`
  - `route_count` = `254`
  - `environment` = `staging`

### postgresql

- status : `degraded`
- latency_ms : `1061.32`
- version : `17.6`
- checked_at : `2026-07-22T14:24:17.641173`
- summary : Latence DB élevée (1061.32 ms)
- error_code : `db_latency_high`
- métriques :
  - `active_connections` = `12`
  - `pool_size` = `5`
  - `max_overflow` = `10`
  - `checked_out` = `1`
  - `available` = `0`
  - `overflow` = `-4`
  - `latency_ms` = `1061.32`
  - `max_connections` = `60`

### jobs_queue

- status : `healthy`
- latency_ms : `259.35`
- version : `v1`
- checked_at : `2026-07-22T14:24:17.927319`
- summary : File jobs nominale
- error_code : `None`
- métriques :
  - `pending` = `0`
  - `running` = `0`
  - `failed` = `0`
  - `completed_recent_count` = `0`
  - `oldest_pending_age_seconds` = `None`
  - `stalled_count` = `0`
  - `completed_total` = `0`

### event_bus

- status : `healthy`
- latency_ms : `250.64`
- version : `v1`
- checked_at : `2026-07-22T14:24:18.195749`
- summary : Bus opérationnel — claim nominal
- error_code : `None`
- métriques :
  - `pending` = `0`
  - `processing` = `0`
  - `failed` = `0`
  - `backlog_count` = `0`
  - `oldest_pending_age_seconds` = `None`
  - `stalled_count` = `0`
  - `pending_events` = `0`

### search

- status : `healthy`
- latency_ms : `626.17`
- version : `v1`
- checked_at : `2026-07-22T14:24:18.841086`
- summary : Index Search disponible
- error_code : `None`
- métriques :
  - `indexed_docs` = `0`
  - `table_exists` = `true`
  - `column_exists` = `true`
  - `column_type` = `tsvector`
  - `gin_index` = `true`
  - `query_ok` = `true`
  - `query_latency_ms` = `626.17`

## PostgreSQL direct

```json
{
  "errors": [],
  "checks": {
    "select_1": "PASS",
    "version": "17.6",
    "active_connections": 12,
    "max_connections": 60,
    "pool_size": 5,
    "checked_out": 1
  }
}
```

## Jobs / Events (lecture seule)

```json
{
  "errors": [],
  "checks": {
    "jobs_count": 0,
    "events_count": 0,
    "jobs_groups": {},
    "events_groups": {},
    "completed_with_old_lock": 0,
    "note": "stalled = processing only (completed exclus)"
  }
}
```

## Search (lecture seule)

```json
{
  "errors": [],
  "checks": {
    "count_before": 0,
    "search_vector_type": "tsvector",
    "gin_index": true,
    "count_after": 0
  }
}
```

## Endpoints admin

```json
{
  "endpoints": {
    "/api/admin/system/health": {
      "status_code": 200,
      "secrets": [],
      "ok": true,
      "service_ids": [
        "api",
        "postgresql",
        "jobs_queue",
        "event_bus",
        "search",
        "billing",
        "notifications",
        "authentication",
        "vault",
        "storage",
        "ai",
        "ocr"
      ]
    },
    "/api/admin/system/metrics?period=24h": {
      "status_code": 200,
      "secrets": [],
      "ok": true
    },
    "/api/admin/system/alerts": {
      "status_code": 200,
      "secrets": [],
      "ok": true
    },
    "/api/admin/system/logs?limit=20": {
      "status_code": 200,
      "secrets": [],
      "ok": true
    }
  },
  "errors": []
}
```

## Erreurs

- aucune

## Absence de secrets

- DATABASE_URL complète : non exposée
- mots de passe / clés API / service_role : non détectés dans les sorties contrôlées
- stack traces : non exposées dans les résultats providers / endpoints

## Recommandations

- Conserver le défaut `mock` en CI ; activer `real` uniquement en staging/prod.
- Remettre l’hôte réel dans `ELFIS_PERFORMANCE_DATABASE_URL` (placeholder `db.xxxxxxxxx.supabase.co` détecté ; récupéré depuis le rapport RC1 pour cette run).
- PostgreSQL `degraded` ici = latence remote Supabase (~1 s) au-dessus du seuil staging degraded (800 ms) mais sous unhealthy (3000 ms). SELECT 1 OK, version 17.6, pool lisible.
- Ajuster `SYSTEM_HEALTH_POSTGRES_LATENCY_*_MS` selon la topologie (local vs distant).
- Surveiller jobs/events degraded (backlog) sans alerter sur completed anciens.
- Si métriques PG partielles (pg_stat_activity) → accepter `degraded`, pas d’exception globale.
- Brancher ensuite Billing / AI / OCR uniquement après validation métier.

## Décision

**PASS** — les cinq providers réels répondent sur PostgreSQL staging ; endpoints admin 200 ; aucun secret exposé ; Search (tsvector + GIN) conforme ; jobs/events en lecture seule avec compteurs à zéro.

Aucun commit. Aucun push. Aucune migration exécutée par cette validation.
