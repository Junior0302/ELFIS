# Runbook — Product Delivery Reconciliation

## Quand

Livraisons en `unknown`, `delivering` (lease expirée), ou `manual_review`.

## Commande

```bash
python -m scripts.product_integrations.reconcile --product comptapilot --status unknown --dry-run
python -m scripts.product_integrations.reconcile --delivery-id <id> --apply --confirm
```

## Règles

| Distant | Local |
|---------|-------|
| delivered confirmé | → delivered |
| dry-run confirmé | → validated_not_delivered |
| inconnu | → manual_review (pas failed auto) |
| absent sûr | → queued retry si tentatives restantes |

Aucun payload métier dans les logs d’audit.
