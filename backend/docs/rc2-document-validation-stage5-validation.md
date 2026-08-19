# RC2.5.5 — Validation métier & bridge ComptaPilot

## Staging

```
python scripts/rc2/validate_document_validation_stage5_staging.py
```

Bridge ComptaPilot réel : désactivé ; script dédié à activer explicitement seulement en labo.

## Activation labo

1. Appliquer SQL stage5
2. `DOCUMENT_BUSINESS_VALIDATION_ENABLED=true`
3. Extraction confirmée + validation valide
4. Pour publication : `PRODUCT_DOCUMENT_BRIDGE_ENABLED=true` + `COMPTAPILOT_DOCUMENT_PUBLISH_ENABLED=true`
5. Worker CLI pour livraisons
