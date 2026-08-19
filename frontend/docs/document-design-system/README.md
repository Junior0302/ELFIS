# Document Design System V1 — F1.3.4

Design system premium pour **facture / devis / avoir** + choix Avec/Sans logo à l’étape Vérification.

## Livrables

| Doc | Contenu |
|-----|---------|
| [01-runtime-audit.md](./01-runtime-audit.md) | Audit runtime PDF + divergences |
| [02-architecture.md](./02-architecture.md) | Architecture composants DDS |
| [03-premium-layout.md](./03-premium-layout.md) | Structure premium brief C |
| [04-brand-identity.md](./04-brand-identity.md) | Identité org (logo, couleurs) |
| [05-logo-choice.md](./05-logo-choice.md) | Choix logo à Vérification |
| [06-permissions.md](./06-permissions.md) | Permissions show/hide vs replace |
| [07-unified-config.md](./07-unified-config.md) | Config unique preview/PDF/email/Vault |
| [08-doc-types.md](./08-doc-types.md) | Métadonnées devis / avoir / facture |
| [09-test-plan.md](./09-test-plan.md) | DDS01–DDS40 + DP01–DP25 |
| [10-implementation-report.md](./10-implementation-report.md) | Rapport d’implémentation |
| [11-go-nogo.md](./11-go-nogo.md) | Critères GO (15 points) |
| [12-changelog.md](./12-changelog.md) | Changelog F1.3.4 |

## Code

- Backend : `backend/app/services/document_branding.py`, `sales_pdf.py`
- Frontend : `frontend/src/comptapilot/facturation/document-design-system/`
- UI Vérification : `FacturationComposerPage` + `IdentityVisualSection`

## Hors scope

- **F1.4 non démarré**
- Pas de second moteur PDF
- Pas de mentions légales inventées
- Pas de hardcode CreaLab Auto / ComptaPilot sur PDF client
