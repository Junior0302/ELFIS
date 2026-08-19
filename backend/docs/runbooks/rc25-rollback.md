# Runbook — Rollback RC2.5

1. Flags off (validation, bridge, publish, auto_enqueue).
2. Stopper workers processing + product_integrations.
3. Ne pas dropper les tables (non destructif).
4. Conserver traces packages/deliveries pour audit.
5. Revert code déployé si nécessaire (sans migration destructive).
6. Escalade : incident platform + audit `PRODUCT_DOCUMENT_DELIVERY_*`.
