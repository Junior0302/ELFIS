# ELFIS Observability V1

## Request / Correlation IDs

Middleware lit `X-Request-Id` / `X-Correlation-Id` (remplace si invalides), les stocke en contextvars, les renvoie en headers réponse, et les propage via `inject_correlation` / champs existants `correlation_id`.

## Logs

Format JSON par défaut (`ELFIS_LOG_FORMAT=json`). Corps requête/réponse **non** loggés (`ELFIS_LOG_INCLUDE_*_BODY=false`).

## Métriques

Registre mémoire : HTTP, rate limits, extensible jobs/events/AI.  
`GET /api/metrics` (auth admin ou `X-Metrics-Token`)  
`GET /api/platform/observability/metrics`

## Health

- `GET /api/health/live` — process OK
- `GET /api/health/ready` — DB + tables critiques + config (pas d’appel Stripe/OpenAI)
- `GET /api/health/details` — platform admin

L’ancien `GET /api/health` reste inchangé.
