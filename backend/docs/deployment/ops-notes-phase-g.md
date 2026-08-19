# Feature flags, versioning events/jobs, monitoring — Phase G

## Feature flags (inventaire)

| Flag | Défaut typique | Prod recommandée | Impact | Rollback |
|------|----------------|------------------|--------|----------|
| `ELFIS_BILLING_ENABLED` | true | true | Billing off = pas de Stripe | env |
| `ELFIS_BILLING_ENFORCE_ENTITLEMENTS` | false | **true** (décision produit) | Accès features | env |
| `ELFIS_BILLING_ENFORCE_QUOTAS` | false | **true** | Uploads/IA limités | env |
| `ELFIS_AI_ENABLED` | true | selon offre | Kill-switch IA | env + runbook |
| `ELFIS_OCR_ENABLED` | false | false jusqu’à activation | awaiting_ocr | env |
| `ELFIS_OCR_PROVIDER` | disabled | disabled/mock interdit | — | env |
| `ELFIS_DOCUMENT_INTELLIGENCE_ENABLED` | true | true | Pipeline DI | env |
| `ELFIS_ACCOUNTING_PIPELINE_ENABLED` | true | true | Comptabilité | env |
| `ELFIS_SEARCH_ENABLED` | true | true | Search | env |
| `ELFIS_CLEANUP_ENABLED` | false | false | Purge technique | env |
| `ELFIS_CLEANUP_DRY_RUN` | true | true si cleanup | Aucune suppression | env |
| `ELFIS_EVENT_WORKER_ENABLED` | false (API) | workers dédiés | Bus | process |
| `ELFIS_JOB_WORKER_ENABLED` | false (API) | workers dédiés | Jobs | process |
| `ELFIS_HSTS_ENABLED` | selon config | true | Headers | env |

Les flags de sécurité critiques ne doivent pas rester désactivés par accident en production (validateur + checklist).

## Event versioning (`.v1`)

- Ajout de champs **optionnels** autorisé
- Suppression / changement de sens **interdit** → créer `.v2`
- Workers : compatibilité pendant transition ; ne pas déployer un consumer qui refuse les anciens payloads tant que la file n’est pas drainée

## Job payload versioning

- Préférer champs optionnels + defaults
- Jobs en `pending`/`retry` doivent rester traitables après déploiement
- Dead-letter : diagnostic manuel (pas de réparation auto dangereuse)
- Rollback app : payloads `.v1` doivent rester lisibles

## Rate limiting multi-instance

Le limiteur mémoire V1 **n’est pas partagé** entre replicas.  
Risque : N× limite effective.  
Avant scale horizontal : gateway / Redis (hors Phase G).

## Outbox transactionnelle

Risque : commit métier OK, crash avant publish event → pipeline non démarré.  
Détection : requêtes diagnostic (documents sans extraction, delivery sans job, events pending anciens) — **pas de réparation auto** dans cette phase.  
Décision archi : Outbox V2 recommandée.

## États orphelins détectables (diagnostic lecture)

- Document archivé sans extraction
- Analyse completed sans proposition
- Delivery pending sans job
- Subscription legacy divergente
- Job running sans heartbeat
- Event pending ancien
- Notification attendue absente

## Grace period workers / API

Recommandation initiale : **30–60 s** termination grace (finaliser le job courant ou le laisser récupérable via stale lock).
