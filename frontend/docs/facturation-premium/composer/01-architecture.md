# 01 — Architecture

## Composer Framework (générique)

Emplacement : `frontend/src/composer-framework/`

Miroir de `widget-framework` / `wizard-framework` — **produit-agnostique**.

### Primitives

| Composant | Rôle |
|-----------|------|
| `ComposerLayout` | Shell 3 colonnes + header/footer |
| `ComposerHeader` | Titre, type, statut, autosave, actions |
| `ComposerSidebar` | Étapes (terminé / en cours / bloqué / erreur) |
| `ComposerBody` | Zone éditeur |
| `ComposerInspector` | Propriétés (totaux, échéance, notes…) |
| `ComposerPreview` | Aperçu PDF / structuré |
| `ComposerFooter` / `ComposerNavigation` | Navigation étapes |
| `ComposerToolbar` / `ComposerActions` | Actions |
| `ComposerProgress` / `ComposerStatus` | Progression + sauvegarde |
| `ComposerValidation` | Issues info/warning/error/suggestion |
| `ComposerSection` / `ComposerCard` | Contenu éditeur |
| `useComposerFocus` | Focus mode + sorties |

### Intégration Facturation

`FacturationComposerPage` consomme :

- `FACTURATION_WORKFLOW_STEPS` + `useWizardNavigation` (F1.0)
- `deriveWizardControls` / `draftAmount*` (helpers existants)
- APIs `createSalesDoc` / `updateSalesDoc` / `openSalesDocPdfBlob` / `downloadSalesDocPdf` / `billingAction`

Aucune modification Vault / Billing moteur / Financial Engine / SalesPilot / InventoryPilot.
