# Comment exécuter la recette fonctionnelle ELFIS Core

## Prérequis

- Python 3.12+ avec venv `backend/.venv`
- Node.js pour le frontend
- Windows PowerShell (commandes ci-dessous)
- Aucune clé API réelle requise pour la recette locale

## Installation

```powershell
cd "C:\Users\Black\Desktop\elfis core\backend"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd ..\frontend
npm install
```

## Variables

```powershell
cd backend
Copy-Item .env.test-functional.example .env.test-functional
# Charger (exemple simple) :
Get-Content .env.test-functional | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $k,$v = $_.Split('=',2); Set-Item -Path "Env:$k" -Value $v
}
```

`ELFIS_ENVIRONMENT=test` — jamais `production`.

## Base & seed

```powershell
cd backend
$env:ELFIS_ENVIRONMENT='test'
$env:DATABASE_URL='sqlite:///./elfis_functional_recette.db'
python scripts/reset_functional_test_db.py
```

PostgreSQL local (recommandé pour FTS) :

```powershell
$env:DATABASE_URL='postgresql+psycopg://elfis:elfis@localhost:5432/elfis_functional_recette'
# Appliquer dans l'ordre les SQL de backend/sql/*.sql puis :
python scripts/reset_functional_test_db.py
```

## Migrations SQL (ordre recommandé)

1. `vault_postgres.sql`
2. `elfis_event_bus_postgres.sql`
3. `elfis_notifications_postgres.sql`
4. `elfis_job_queue_postgres.sql`
5. `elfis_ai_engine_postgres.sql`
6. `elfis_document_intelligence_postgres.sql`
7. `elfis_accounting_pipeline_postgres.sql`
8. `elfis_search_engine_postgres.sql`
9. `elfis_billing_postgres.sql`
10. `elfis_platform_admin_postgres.sql`
11. `elfis_security_observability_postgres.sql`

Sous SQLite de recette, `Base.metadata.create_all` + `init_db()` suffisent pour les scénarios automatiques.

## Lancement API / workers / frontend

**Important :** le proxy Vite pointe vers le port **8000**. Aligner le backend.

```powershell
# Terminal 1 — API
cd backend
.\.venv\Scripts\Activate.ps1
$env:ELFIS_ENVIRONMENT='test'
$env:DATABASE_URL='sqlite:///./elfis_functional_recette.db'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Job worker (parcours async)
$env:ELFIS_JOB_WORKER_ENABLED='true'
python -m app.jobs.job_worker

# Terminal 3 — Event worker
$env:ELFIS_EVENT_WORKER_ENABLED='true'
python -m app.events.event_worker

# Terminal 4 — Frontend
cd frontend
npm run dev -- --port 5173
```

## Auth — point d’attention

`POST /api/auth/login` est **désactivé** (Firebase).  

- **Tests API / scripts** : JWT via `create_access_token` (helpers `login_user`).  
- **Recette UI manuelle** : comptes Firebase Auth de test mappés aux mêmes e-mails, ou injecter un token de recette.

Mot de passe seed (si hash utilisé hors Firebase) : `ElfisRecette!Test-2026`

## Lancer les tests

```powershell
cd backend
python scripts/run_functional_validation.py --reset-db --verbose
# ou
python -m pytest tests/functional -q
```

### Phase A uniquement (auth / orgs / rôles / isolation)

```powershell
cd backend
$env:ELFIS_ENVIRONMENT='test'
$env:DATABASE_URL='sqlite:///./elfis_functional_recette.db'
python scripts/run_functional_validation.py --reset-db --phase-a
```

Exécute les 6 scénarios `test_phase_a_*.py` + `tests/security` + `tests/platform_admin`, puis vérifie l’import FastAPI. Rapport : `docs/functional-test-phase-a-report.md`.

### Phase B uniquement (billing / essai / quotas)

```powershell
cd backend
$env:ELFIS_ENVIRONMENT='test'
$env:DATABASE_URL='sqlite:///./elfis_functional_recette.db'
python scripts/run_functional_validation.py --reset-db --phase-b
```

Exécute les 11 scénarios `test_phase_b_*.py` + `tests/billing` + Stripe/access, avec enforcement activé pour le process. Rapport : `docs/functional-test-phase-b-report.md`.

### Phase C uniquement (documents / vault / DI / AI / accounting)

```powershell
cd backend
$env:ELFIS_ENVIRONMENT='test'
$env:DATABASE_URL='sqlite:///./elfis_functional_recette.db'
python scripts/run_functional_validation.py --reset-db --phase-c
```

Exécute les 14 scénarios `test_phase_c_*.py` + vault/DI/AI/accounting/jobs/events/notifications/search. Stockage Vault mocké (pas de Supabase). Rapport : `docs/functional-test-phase-c-report.md`.

Options :

- `--phase-a`
- `--phase-b`
- `--phase-c`
- `--functional-only`
- `--backend-only`
- `--skip-frontend`
- `--reset-db`

## Reset

```powershell
python scripts/reset_functional_test_db.py
```

Le script refuse `production` et les URL sans `test`/`functional`/`recette` (sauf SQLite).

## Diagnostic

1. Vérifier `X-Request-Id` / `X-Correlation-Id` dans la réponse.  
2. Consulter logs (pas de secrets).  
3. Remplir `docs/functional-test-report-template.md`.  
4. Relancer le scénario après `reset_functional_test_db.py`.

## Nettoyage

Supprimer `backend/elfis_functional_recette.db` et le dossier `tests/functional/fixtures/documents/*.pdf` générés si besoin.
