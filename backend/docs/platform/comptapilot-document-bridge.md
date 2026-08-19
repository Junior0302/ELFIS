# ComptaPilot Document Bridge (RC2.5.5)

## Décision d’intégration

**Stratégie A — adaptateur de service versionné** (`ComptaPilotServiceAdapter`).

Motifs :

- pas d’outbox transactionnel strict fiable pour ce flux ;
- éviter un import profond (`AccountingMapper`, tables Invoice, écritures) ;
- bridge **désactivé par défaut**.

## Flags

```
PRODUCT_DOCUMENT_BRIDGE_ENABLED=false
PRODUCT_DOCUMENT_BRIDGE_DEFAULT=noop
COMPTAPILOT_DOCUMENT_PUBLISH_ENABLED=false
COMPTAPILOT_DOCUMENT_AUTO_PUBLISH=false
COMPTAPILOT_REQUIRE_CONFIRMED_EXTRACTION=true
COMPTAPILOT_REQUIRE_VALID_BUSINESS_VALIDATION=true
```

## Ce que le bridge ne fait pas

- aucun compte / journal / débit / crédit ;
- aucune écriture dans les tables métier ComptaPilot ;
- aucun appel OpenAI ;
- aucune lecture du fichier original hors package validé.

## Worker

```
python -m scripts.product_integrations.worker --once --product comptapilot
```

Jamais démarré automatiquement dans le processus API production.
