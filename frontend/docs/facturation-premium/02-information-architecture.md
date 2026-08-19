# 02 — Architecture d’information

## Espaces Facturation (officiels)

```
Facturation
├── Vue d’ensemble     → /facturation
├── Documents          → /facturation/documents
├── Nouveau document   → /facturation/nouveau
├── Catalogue          → /facturation/catalogue → redirect /catalogue
└── Activité           → /facturation/activite  → redirect /activites
```

## Compatibilité legacy

| Route | Comportement |
|-------|----------------|
| `/facturation` | Vue d’ensemble ; `?doc=` → documents ; `?customer_id=` → nouveau |
| `/devis` | Conservée (CRUD devis historique) |
| `/catalogue` | Conservée |
| `/activites` | Conservée |
| `/quotes`, `/catalog`, `/sales/*` | Redirects existants |

## Navigation ComptaPilot

`navModel` catégorie `ventes` / label **Facturation** mise à jour vers les 5 espaces. Pas d’entrée SalesPilot dans cette catégorie.

## Layout

`FacturationLayout` : sous-navigation espaces + `<Outlet />`.
