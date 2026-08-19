# ELFIS Security V1

## Protections actives

- Middleware HTTP : méthodes, taille payload, rate limiting catégorisé, headers, request/correlation IDs
- Headers : `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP
- CSP en **report-only** par défaut (`ELFIS_CSP_REPORT_ONLY=true`) — compatible Stripe / Firebase
- HSTS : **off** par défaut ; activer `ELFIS_HSTS_ENABLED=true` en production HTTPS uniquement
- Erreurs normalisées `{ error: { code, message, request_id, correlation_id, details } }` + `detail` legacy
- Redaction centrale (password, token, secret, prompt, stripe_signature, …)
- Validation fichiers centralisée (`validate_uploaded_file`)
- Audit `elfis_security_events` (sans credentials)
- JWT HS256 inchangé ; `iss`/`aud` préparés, imposés seulement si `ELFIS_JWT_ENFORCE_ISSUER_AUDIENCE=true`

## Rate limiting

Backend mémoire V1 (`ELFIS_RATE_LIMIT_BACKEND=memory`). Catégories : auth, upload, ai, search, email, billing, platform_admin, webhook.

Réponse `429` + `Retry-After` + code `rate_limit_exceeded`.

Webhooks Stripe : limite large, clé sans IP seule (retries légitimes).

## Permissions

`require_permission(code)` centralise les mappings modules → RBAC existant. Pas de nouveau RBAC avancé.

## Limites V1

- Pas d’antivirus complet
- Pas de Redis obligatoire
- Pas de MFA / OAuth entreprise
- Issuer/audience JWT non imposés tant que le flag enforce est false

## Secrets

Ne jamais logger tokens, mots de passe, payloads Stripe, prompts, PDF, corps e-mail.
