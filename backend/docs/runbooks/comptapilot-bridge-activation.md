# Runbook — Activation bridge ComptaPilot

## Séquence progressive

| Phase | Flags |
|-------|-------|
| 0 | Tout off |
| 1 | `DOCUMENT_BUSINESS_VALIDATION_ENABLED=true` — pas de packages |
| 2 | Packages manuels + bridge `noop` |
| 3 | `PRODUCT_DOCUMENT_BRIDGE_ENABLED=true` + `COMPTAPILOT_DOCUMENT_BRIDGE_MODE=dry_run` |
| 4 | Live manuel org pilote + `--confirm-live` staging |
| 5 | Plusieurs orgs pilotes |
| 6 | Auto-publish = **hors scope RC2.5.6** |

## Désactivation d’urgence

`COMPTAPILOT_DOCUMENT_BRIDGE_MODE=disabled` + `COMPTAPILOT_DOCUMENT_PUBLISH_ENABLED=false`.

## Interdits

- Pas d’AccountingMapper dans ELFIS
- Pas d’écritures / journaux / comptes
- Pas de document utilisateur réel en staging live
