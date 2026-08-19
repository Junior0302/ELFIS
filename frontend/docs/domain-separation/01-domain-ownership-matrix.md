# 01 — Matrice de propriété des domaines

## Règle

| Si… | Alors propriétaire |
|-----|-------------------|
| Sert plusieurs Pilot | **ELFIS Core** |
| Cycle commercial avant facture | **SalesPilot** |
| Facture fiscale / paiement / compta | **ComptaPilot** |

## Matrice objets

| Objet | Domaine | Lecteurs | Écrivains | Route actuelle | Route cible | Table / source | Risque | Stratégie S1.0 |
|-------|---------|----------|-----------|----------------|-------------|----------------|--------|----------------|
| Organisation | ELFIS | Tous Pilot | ELFIS | `/organisation` | `/platform/settings` → org | org | Moyen | UI → Core ; lecture Compta pour PDF |
| Utilisateur / membres | ELFIS | Tous | ELFIS | `/admin/equipe` | `/platform/settings` | memberships | Faible | Menu Compta → Core |
| Rôles / permissions | ELFIS | Tous | ELFIS | équipe | platform settings | roles | Faible | Idem |
| Contact / Party | ELFIS | Sales, Compta | ELFIS | `/clients` (vue) | `/platform/relations/*` | customers / contacts | Moyen | Vues métier temporaires, pas de fusion tables |
| Client (rôle billing) | ELFIS id + vue Compta | Compta, Sales | Compta (billing attrs) | `/clients` | Core + vue Compta | customers | Moyen | Adapter lecture ; migration tables → S1.2+ |
| Fournisseur | ELFIS + vue Compta | Compta | Compta | `/fournisseurs` | Core + vue Compta | contacts type | Moyen | Idem |
| Prospect / Lead | Sales | Sales | Sales | `/sales/leads` | `/sales/leads` | sales leads | Faible | Déjà Sales |
| Opportunité | Sales | Sales | Sales | `/sales/pipeline` | `/sales/pipeline` | deals | Faible | Déjà Sales |
| Devis commercial | Sales (cible) | Sales, Compta | Sales | `/devis` | `/sales/proposals` ou `/sales/quotes` | invoices quote | **Élevé** | Routes legacy ; badge → SalesPilot |
| Catalogue / tarifs | Sales (cible) | Sales, Compta | Sales | `/catalogue` | `/sales/catalog` | catalog | Moyen | Redirect alias + badge |
| Activités commerciales | Sales (cible) | Sales | Sales | `/activites` vs `/sales/activities` | Sales | mixed | Moyen | Clarifier ; ne pas fusionner |
| Facture définitive | Compta | Compta | Compta | `/facturation` | `/facturation` | invoices | Faible | Reste Compta |
| Paiement | Compta | Compta | Compta | facturation | Compta | payments | Faible | Reste |
| TVA / clôture / écritures | Compta | Compta | Compta | `/tva`, `/cloture`, `/accounting/*` | Compta | accounting | Faible | Reste |
| Document Vault | ELFIS | Pilot filtrés | ELFIS Vault | `/documents` | `/platform/documents` | vault | Moyen | Vue filtrée Compta ; Vault unique |
| E-mail / Brevo | ELFIS | Compta (envoi) | ELFIS | delivery | Core communications | mailer | Faible | Déjà Core |
| Banque (connexion) | ELFIS service | Compta | ELFIS | `/banque` | Core integrations + vue Compta | banking | Moyen | UI Compta temporaire |
| Assistant / Aura | ELFIS Aura | Tous | ELFIS | `/copilote` | `/platform/aura` | copilote | Moyen | Renommer « financier » ; Aura → Home |

## Flux facture (cible)

```
Prospect → SalesPilot
    ↓
Devis accepté → SalesPilot
    ↓
intent invoice.create → Orchestrator
    ↓
Facture fiscale → ComptaPilot
    ↓
PDF + Vault + Email → ELFIS
    ↓
Paiement / écriture → ComptaPilot
```

SalesPilot **ne crée pas** la facture définitive directement.
