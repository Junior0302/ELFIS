# Configuration environnement — Security / Observability / Reliability

Voir aussi `backend/.env.example`.

## Environnements

| Valeur | Comportement |
|--------|----------------|
| development | logs adaptés, secrets faibles → warning, HSTS off |
| test | SQLite OK, pas de réseau requis |
| staging | proche prod, Stripe test |
| production | Postgres, CORS strict, fatals bloquent le démarrage |

Variable : `ELFIS_ENVIRONMENT` (sinon `APP_ENV`).

## Variables clés

- Sécurité : `ELFIS_SECURITY_HEADERS_*`, `ELFIS_CSP_*`, `ELFIS_HSTS_ENABLED`, `ELFIS_RATE_LIMIT_*`, `ELFIS_JWT_*`
- Logs : `ELFIS_LOG_LEVEL`, `ELFIS_LOG_FORMAT`, `ELFIS_LOG_INCLUDE_*_BODY`
- Métriques : `ELFIS_METRICS_ENABLED`, `ELFIS_METRICS_REQUIRE_AUTH`, `ELFIS_METRICS_TOKEN`
- Reliability : `ELFIS_CLEANUP_*`, `ELFIS_STALE_*`, `ELFIS_RETENTION_*`

Ne jamais committer de secrets réels.
