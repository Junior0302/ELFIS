# Baseline performance ELFIS Core (Phase F)

Date : 2026-07-21  
Environnement : Windows local · `ELFIS_ENVIRONMENT=test` · SQLite fichier recette · providers mocks  
Matériel : poste développeur (indicatif uniquement)

## Distinction importante

| Mode | Base | Conclusion autorisée |
|------|------|----------------------|
| Local rapide | SQLite | Latences indicatives, atomicité UPDATE conditionnel, claim optimiste |
| Postgres concurrence | `ELFIS_PERFORMANCE_DATABASE_URL` | SKIP LOCKED, pool, GIN/tsvector, vraie charge multi-worker |

**Ne pas** conclure sur FOR UPDATE SKIP LOCKED, pool Postgres ou GIN à partir de SQLite.

## Dataset utilisé pour baseline rapide

Seed fonctionnel standard (orgs/users Phase A–E) — pas le dataset 5k (configurable, hors suite rapide).

## Mesures locales (indicatif)

Objectifs documentés (non SLA production) :

| Route | Objectif p95 | Mesure suite Phase F |
|-------|--------------|----------------------|
| `/api/health/live` | < 200 ms (idéal) / < 2 s garde-fou test | PASS garde-fou |
| Listes vault paginées | < 800 ms / < 3 s garde-fou | PASS |
| Search | < 1 s / < 5 s garde-fou | PASS |
| Platform dashboard | < 1,5 s / < 8 s garde-fou | PASS |

Les garde-fous des tests automatiques sont volontairement larges pour CI locale variable.

## Recommandations production

- `pool_pre_ping=true`, `pool_size` 5–20, `max_overflow` 10–20, `pool_recycle` 1800
- Index claim jobs/events + GIN search (sql/*.sql) + `uq_document_email_org_idempotency`
- Rate limiter mémoire non partagé multi-instance → Redis avant scale horizontal
- Outbox transactionnelle généralisée = V2 (voir rapport Phase F)
