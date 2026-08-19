# Runbook — Document Processing Worker

## Démarrage

```bash
python -m scripts.document_processing.worker --once
# ou boucle
python -m scripts.document_processing.worker --poll-seconds 2
```

## Arrêt / drain

1. Stopper les nouveaux enqueues (`DOCUMENT_*_AUTO_ENQUEUE=false`).
2. Laisser le worker consommer jusqu’à backlog 0.
3. SIGTERM / Ctrl+C — leases expirent et sont reprises.

## Lease

- Claim : `FOR UPDATE SKIP LOCKED`
- Heartbeat / `locked_until`
- Après crash : reclaim si lease expirée

## Logs autorisés

job_id, pipeline_key, status, error_code, durée — **pas** OCR, montants, payloads.
