# F1.3.1 — UX Review Pass 1 (Facturation zero friction)

Corrige les irritants UX validés par revue manuelle. **Aucune** nouvelle capacité métier. Pas F1.4.

## Documents

| Fichier | Contenu |
|---------|---------|
| [01-runtime-audit-pass-1.md](./01-runtime-audit-pass-1.md) | Audit runtime (cause exacte → correction) |
| [02-documents-entry.md](./02-documents-entry.md) | Documents = entrée unique |
| [03-popin-new-document.md](./03-popin-new-document.md) | Pop-in Nouveau document |
| [04-freeform-composer.md](./04-freeform-composer.md) | Composer freeform |
| [05-picker-behavior.md](./05-picker-behavior.md) | Pickers closed-by-default |
| [06-validation-dedup.md](./06-validation-dedup.md) | Déduplication validations |
| [07-focus-header-pdf.md](./07-focus-header-pdf.md) | Focus / header / PDF (+ Full Focus) |
| [08-responsive.md](./08-responsive.md) | Responsive |
| [09-test-plan.md](./09-test-plan.md) | UXF01–40 + MR01–30 |
| [10-implementation-report.md](./10-implementation-report.md) | Rapport GO / NO GO Pass 1 |
| [11-full-focus-mode-audit.md](./11-full-focus-mode-audit.md) | F1.3.1.1 audit Full Focus |
| [12-composer-focus-layout.md](./12-composer-focus-layout.md) | ComposerFocusLayout (dans modal) |
| [13-focus-routing.md](./13-focus-routing.md) | Routing modal Documents |
| [14-focus-responsive.md](./14-focus-responsive.md) | Responsive Full Focus |
| [15-full-focus-test-plan.md](./15-full-focus-test-plan.md) | FF01–40 + MF01–25 |
| [16-full-focus-implementation-report.md](./16-full-focus-implementation-report.md) | Rapport GO F1.3.1.1 (supersédé UX) |
| [17-modal-composer-audit.md](./17-modal-composer-audit.md) | F1.3.1.2 audit modal |
| [18-modal-route-strategy.md](./18-modal-route-strategy.md) | Stratégie route nested |
| [19-composer-dialog-layout.md](./19-composer-dialog-layout.md) | Layout ComposerDialog |
| [20-modal-close-flow.md](./20-modal-close-flow.md) | Fermeture / fin de flux |
| [21-modal-composer-test-plan.md](./21-modal-composer-test-plan.md) | MC01–40 + MD01–25 |
| [22-modal-composer-implementation-report.md](./22-modal-composer-implementation-report.md) | Rapport GO F1.3.1.2 |
| [23-modal-composer-changelog.md](./23-modal-composer-changelog.md) | Changelog modal |
| [24-modal-composer-regression-diagnostic.md](./24-modal-composer-regression-diagnostic.md) | F1.3.1.3 diagnostic régression |
| [25-composer-modal-state-machine.md](./25-composer-modal-state-machine.md) | State machine unique |
| [26-document-creation-modal-root.md](./26-document-creation-modal-root.md) | Root modal persistant |
| [27-modal-transition-type-to-composer.md](./27-modal-transition-type-to-composer.md) | Transition petite → grande |
| [28-modal-router-strategy.md](./28-modal-router-strategy.md) | Router modal robuste |
| [29-modal-errors-and-focus.md](./29-modal-errors-and-focus.md) | Erreurs & focus |
| [30-modal-workflow-test-plan.md](./30-modal-workflow-test-plan.md) | MM01–40 + MV01–20 |
| [31-modal-workflow-go-nogo.md](./31-modal-workflow-go-nogo.md) | Rapport GO F1.3.1.3 |
| [32-guided-composer-runtime-audit.md](./32-guided-composer-runtime-audit.md) | F1.3.2 audit contenu guidé |
| [33-composer-step-state-machine.md](./33-composer-step-state-machine.md) | Machine ComposerStep |
| [34-guided-step-content.md](./34-guided-step-content.md) | Contenu des 6 étapes |
| [35-guided-layout-pdf.md](./35-guided-layout-pdf.md) | Layout PDF sticky |
| [36-guided-validation-a11y.md](./36-guided-validation-a11y.md) | Validation & a11y |
| [37-guided-composer-test-plan.md](./37-guided-composer-test-plan.md) | GC01–40 + GM01–25 |
| [38-guided-composer-changelog.md](./38-guided-composer-changelog.md) | Changelog guidé |
| [39-guided-composer-go-nogo.md](./39-guided-composer-go-nogo.md) | Rapport GO F1.3.2 |

## Nav finale

Vue d’ensemble | Documents | Catalogue | Activité

Création : pop-in type → **ComposerDialog guidé** (6 étapes) sur `/facturation/documents/new?type=` (Documents monté derrière). Legacy `/nouveau` redirige.
