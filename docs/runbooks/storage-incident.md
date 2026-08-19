# Runbook — Incident storage (Vault / Supabase)

## Objectif
Gérer indisponibilité ou erreurs storage sans fuite de données.

## Actions
1. Confirmer `SUPABASE_URL` / service role (sans les logger).
2. Health : vault peut être `degraded` — API reste disponible en lecture selon design.
3. Bloquer uploads si corruption suspectée.
4. Vérifier isolation chemins tenant (`organization_id`).
5. Pas d’URL publiques permanentes.

## Remédiation
- Rotation clé si fuite suspectée (`secret-rotation.md`)
- Restore objets depuis backup storage hébergeur si disponible

## Ne jamais
- Exposer service role au frontend
- Servir des buckets publics pour documents comptables
