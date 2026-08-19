# Document Processing Worker

## Lancement

```bash
export ELFIS_ENVIRONMENT=staging   # requis
python -m scripts.processing.worker --once
python -m scripts.processing.worker --poll-seconds 2 --max-jobs 5 --worker-id dp-1
```

Options : `--once`, `--poll-seconds`, `--worker-id`, `--max-jobs`, `--pipeline`, `--database-url`.

## Comportement

1. Claim jobs (SKIP LOCKED / SQLite)
2. Exécuter étapes via orchestrateur
3. Heartbeat / renouvellement lease
4. Retry selon politique
5. SIGTERM → arrêt boucle (étape courante se termine ou reste récupérable)

**Pas de worker auto dans le processus API en production.**

## Configuration

Voir `DOCUMENT_PROCESSING_*` dans Settings (`document_processing_*`).
