# Runbook — Incident workers

## Objectif
Rétablir le traitement jobs / events sans corruption.

## Symptômes
- Jobs `pending` trop anciens
- Jobs `running` sans heartbeat
- Events failed / dead letter
- Queue qui ne drain pas

## Actions
1. Vérifier `/api/health/ready` et connexion DB.
2. Logs worker : `job_worker_start`, erreurs batch.
3. Scale temporaire : **une** version de worker à la fois pour un type de job.
4. SIGTERM : laisser le grace period (recommandé 30–60s) ; jobs courants finalisés ou récupérables via stale lock.
5. Redémarrer workers ; surveiller claim.

## Diagnostic requêtes (lecture seule)
- Jobs running heartbeat trop vieux
- Events pending > N minutes
- Dead letters récentes

## Ne jamais
- Supprimer des jobs métier sans analyse
- Lancer deux versions incompatibles en parallèle
