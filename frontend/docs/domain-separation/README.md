# Séparation des domaines ELFIS

## Décision

| Domaine | Rôle |
|---------|------|
| **ELFIS Core** | Services, données et capacités partagés |
| **SalesPilot** | Cycle commercial **avant** facturation |
| **ComptaPilot** | Facturation définitive, paiements, comptabilité, finance |

## Règles

1. Une donnée → un propriétaire unique  
2. Multi-Pilot → ELFIS Core  
3. Avant facture fiscale → SalesPilot  
4. Facture / paiement / compta → ComptaPilot  
5. Pilot → Orchestrator → Pilot (jamais Pilot→Pilot direct)  
6. Pas de copie de donnée lors d’un déplacement d’UI  
7. Routes legacy compatibles pendant la transition  

## Index

### S1.0

| Doc | Contenu |
|-----|---------|
| [01-domain-ownership-matrix](./01-domain-ownership-matrix.md) | Propriété des objets |
| [02-current-screen-classification](./02-current-screen-classification.md) | Écrans actuels |
| [03-target-navigation](./03-target-navigation.md) | Menus cibles |
| [04-route-migration-plan](./04-route-migration-plan.md) | Routes & redirects |
| [05-shared-data-contracts](./05-shared-data-contracts.md) | Contrats de lecture |
| [06-transition-backlog](./06-transition-backlog.md) | Backlog S1.x |
| [07-s1-implementation-report](./07-s1-implementation-report.md) | Rapport S1.0 |

### S1.1 — Shared surfaces

| Doc | Contenu |
|-----|---------|
| [08-s11-runtime-audit](./08-s11-runtime-audit.md) | Audit runtime |
| [09-platform-shared-surfaces-architecture](./09-platform-shared-surfaces-architecture.md) | Architecture |
| [10-organization-team-migration](./10-organization-team-migration.md) | Org & équipe |
| [11-vault-documents-migration](./11-vault-documents-migration.md) | Vault |
| [12-communications-migration](./12-communications-migration.md) | Communications |
| [13-aura-migration](./13-aura-migration.md) | Aura |
| [14-relations-shared-view](./14-relations-shared-view.md) | Relations |
| [15-s11-route-migration](./15-s11-route-migration.md) | Routes |
| [16-s11-test-plan](./16-s11-test-plan.md) | Tests |
| [17-s11-implementation-report](./17-s11-implementation-report.md) | Rapport S1.1 |

### S1.2 — Shared Relations

| Doc | Contenu |
|-----|---------|
| [18-s12-relations-model-audit](./18-s12-relations-model-audit.md) | Audit modèles |
| [19-shared-relations-contract](./19-shared-relations-contract.md) | Contrat |
| [20-relations-adapters](./20-relations-adapters.md) | Adapters |
| [21-relations-api](./21-relations-api.md) | API |
| [22-relations-ui](./22-relations-ui.md) | UI |
| [23-relations-permissions](./23-relations-permissions.md) | Permissions |
| [24-relations-migration-strategy](./24-relations-migration-strategy.md) | Migration |
| [25-s12-test-plan](./25-s12-test-plan.md) | Tests |
| [26-s12-implementation-report](./26-s12-implementation-report.md) | Rapport |

## Hors scope S1.2

- Fusion / migration tables  
- Auto-merge  
- Second CRM / Search Engine  
- S1.3  
