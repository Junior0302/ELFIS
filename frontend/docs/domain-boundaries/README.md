# Domaines métier vs plateforme — NAV.DOMAIN.1

Séparation stricte : **ELFIS** = plateforme transversale ; **Finance** / **Commercial** = domaines métier (moteurs ComptaPilot / SalesPilot).

## Statut

| Phase | Scope | Statut |
|-------|--------|--------|
| NAV.CORE.1 | Menu principal ELFIS | Livré |
| **NAV.DOMAIN.1** | Nav Finance / Commercial sans surfaces plateforme | **Livré — STOP captures** |
| **BRAND.ELFIS.1** | Hub Espaces launcher | **Livré — voir [elfis-spaces](../elfis-spaces/)** |
| **BRAND.ELFIS.2** | Identité ELFIS + rôles globaux | **Livré — voir [elfis-brand](../elfis-brand/) — STOP revue** |

## Index

| Doc | Contenu |
|-----|---------|
| [01](./01-platform-vs-domain-contract.md) | Contrat plateforme / domaine |
| [02](./02-finance-navigation.md) | Nav Finance (routes réelles) |
| [03](./03-commercial-navigation.md) | Nav Commercial |
| [04](./04-shared-relations.md) | Relations partagées |
| [05](./05-document-boundaries.md) | Frontières documents |
| [06](./06-settings-boundaries.md) | Paramètres plateforme vs métier |
| [07](./07-contextual-links.md) | Liens contextuels |
| [08](./08-test-plan.md) | ND01–ND30 |
| [09](./09-implementation-report.md) | Rapport GO |
| [10](./10-commercial-nav-parity.md) | Parité accordion Commercial / Finance |

## Modules

- Finance : `frontend/src/navModel.ts` + `ComptaProductNav`
- Commercial : `frontend/src/sales/salesNavModel.ts` + `SalesProductNav`
- Plateforme : `elfisNavigationConfig` (NAV.CORE.1 — inchangé)
