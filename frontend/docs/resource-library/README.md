# ELFIS Resource System — Smart Library V1

**Phase F1.2** · Capacité plateforme transversale  
**Statut :** livré (fondation) — F1.3 Live Document consomme ProductPicker ; **F1.4 non démarré**

## Objectif

Première **Resource Library** officielle pour ComptaPilot (Local Library aujourd’hui, InventoryPilot demain) :

- Abstraction `ResourceSource` + `LocalLibrarySource` branché
- UI Smart Library premium (cartes / liste)
- `ProductPicker` = premier consommateur officiel
- Document Composer (étape produits) branché sur ProductPicker
- Zero UX change prévu au basculement Inventory

## Index

| Doc | Contenu |
|-----|---------|
| [01-runtime-audit.md](./01-runtime-audit.md) | Audit runtime + décisions réutilisation |
| [02-resource-model.md](./02-resource-model.md) | Modèle `Resource` |
| [03-resource-source.md](./03-resource-source.md) | Contrat `ResourceSource` |
| [04-smart-library.md](./04-smart-library.md) | UI Smart Library |
| [05-product-card.md](./05-product-card.md) | Resource Card |
| [06-product-picker.md](./06-product-picker.md) | ProductPicker ↔ Resource System |
| [07-local-library.md](./07-local-library.md) | LocalLibrarySource |
| [08-inventory-ready.md](./08-inventory-ready.md) | Remplacement InventoryPilot |
| [09-roadmap.md](./09-roadmap.md) | Suite (hors F1.3) |
| [10-tests.md](./10-tests.md) | RL01–RL40 |
| [11-implementation-report.md](./11-implementation-report.md) | Rapport de livraison |

## Code

`frontend/src/resource-library/`

Route : `/catalogue` (aliases `/catalog`, `/sales/catalog`, `/facturation/catalogue` → redirect)
