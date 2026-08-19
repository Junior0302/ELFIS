# Platform Developer Cockpit V1

Centre de supervision **technique** séparé du Cockpit Admin métier (`/elfadmin`).

## Accès

- Route UI : `/elfadmin/developer`
- Lien Admin : Ops avancées → **Dev Cockpit**
- Gate FE : `is_platform_admin` (hiérarchie) via `RequireDeveloperCockpit`
- Gate API : `require_developer_cockpit` — flag admin **ou** permissions
  `platform.developer|engineer|sre|cto|admin`
- Les permissions developer/* **ne sont pas** auto-attribuées dans `PLATFORM_ADMIN_PERMISSIONS`

## API agrégateur

Préfixe : `/api/platform/developer/`

| Endpoint | Rôle |
|----------|------|
| `GET /meta` | env, versions, git commit, capabilities |
| `GET /overview` | KPIs jobs/events + services health |
| `GET /services` | service map |
| `GET /config-status` | public + secrets **statut only** |
| `GET /diagnostics` | checks sûrs lecture seule |
| `GET /database-summary` | engine / ping / metadata count |
| `GET /index-collisions` | scan Index() SQLAlchemy |
| `GET /routes` | catalogue FastAPI (pas d'exécution) |
| `GET /capabilities` | pages disponibles / indisponibles |

Réutilise aussi : `/platform/jobs`, `/platform/events`, `/admin/system/logs`, `/admin/audit/events`, AI/notifications/storage existants.

## Sécurité

- Pas de SQL / shell / exécution de routes sensibles
- Secrets : `configured|missing|invalid` uniquement
- Actions jobs retry/cancel : confirmation + audit API existante
- Workers / Feature flags / Traces unifiées : UI **unavailable** (pas de fake data)

## Commandes

```bash
# tests
cd backend && python -m pytest tests/test_developer_cockpit_v1.py -q
cd frontend && npm test -- --run src/developerCockpitNav.test.ts
```
