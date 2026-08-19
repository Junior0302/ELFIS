# Runbook — Product Delivery Worker

## Démarrage

```bash
python -m scripts.product_integrations.worker --once --product noop
python -m scripts.product_integrations.worker --once --product comptapilot --worker-id w1
```

**Jamais** démarrer ce worker dans le processus API production.

## Flags

- `PRODUCT_DOCUMENT_BRIDGE_ENABLED=false` (défaut)
- `COMPTAPILOT_DOCUMENT_BRIDGE_MODE=disabled|dry_run|live`
- `COMPTAPILOT_DOCUMENT_PUBLISH_ENABLED=false` (défaut)
- Auto-publish : **interdit** en RC2.5.6

## Arrêt d’urgence

1. `PRODUCT_DOCUMENT_BRIDGE_ENABLED=false`
2. `COMPTAPILOT_DOCUMENT_BRIDGE_MODE=disabled`
3. Stopper workers
4. Auditer deliveries `unknown` / `manual_review`
