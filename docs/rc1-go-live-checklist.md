# Checklist Go / No-Go — ELFIS CORE v1.0.0 RC1

Légende : `[ ]` à faire · `[x]` fait · `N/E` non exécuté

## RC1.1 — PostgreSQL, migrations, concurrence, staging technique

| Critère | Statut | Notes |
|---------|--------|-------|
| PostgreSQL disponible | N/E | Pas d’instance locale/CI dans la session |
| Backup staging | N/E | |
| Migrations base vide (SQL head) | N/E | Script prêt ; Alembic absent |
| Migrations base existante | N/E | |
| Index vérifiés (Delivery/Stripe/Vault/Jobs/Events/GIN) | N/E | Tests prêts |
| Quota atomique PG | N/E | BLOCKER si fail |
| Accounting atomique | N/E | Suite concurrence |
| Delivery idempotent | N/E | |
| Stripe idempotent | N/E | mock only |
| Vault concurrent | N/E | |
| Jobs SKIP LOCKED | N/E | Tests 100×4 prêts |
| Events SKIP LOCKED | N/E | |
| Pool stable | N/E | |
| Search GIN | N/E | |
| Tenant isolation | N/E | |
| Smoke staging | N/E | flags `--allow-staging` |
| Aucun appel live | [x] | mocks forcés dans scripts RC1 |
| Aucun BLOCKER ouvert | [x] infra / N/E live | |
| Driver `psycopg` | [x] | ajouté requirements |
| Garde-fous reset/prod | [x] | tests unitaires |
| FastAPI import | [x] | |
| Frontend build | voir dernière campagne | |

### Go / No-Go RC1.1

- [ ] **GO RC1.1** uniquement si toutes les lignes live = PASS
- [x] **NO-GO RC1.1** tant que PostgreSQL live n’a pas été exécuté

## Prochaines étapes RC1 (hors RC1.1)

- RC1.2 : staging applicatif bout-en-bout
- RC1.3 : décisions RPO/RTO / rétention
- RC1.4 : plan rate-limit multi-instance + outbox V2 (doc)

## Commandes

```powershell
python scripts/run_functional_validation.py --rc1-postgres
# ou
python scripts/rc1/run_postgres_validation.py --reset-db --migrate --concurrency --performance --search --report
```

Aucun commit. Aucun push.
