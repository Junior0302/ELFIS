# 06 — Backlog de transition

| ID | Item | Priorité | Domaine | Dépendance |
|----|------|----------|---------|------------|
| S1.0 | Nav Compta clarifiée + redirects | Done | Nav | — |
| S1.1 | Hub Relations ELFIS (clients/fournisseurs) | P1 | Core | Layout Core |
| S1.1 | Page Devis sous shell Sales | P1 | Sales | Alias déjà en place |
| S1.1 | Catalogue sous shell Sales | P1 | Sales | Idem |
| S1.1 | Filtre Documents comptables (Vault) | P1 | Compta/Core | API categories |
| S1.2 | Adapter Party / roles sans fusion tables | P1 | Core | Contrats 05 |
| S1.2 | intent `invoice.create` Orchestrator | P2 | Orch | Blueprint P3 |
| S1.3 | Fusion contacts / customers plan migratoire | P2 | Data | Audit usages PDF |
| S1.3 | Aura plateforme vs Assistant financier | P2 | Core | Copilote |
| S1.4 | Paiements / avoirs / récurrentes UI | P2 | Compta | — |
| — | Ne pas : second Vault, second CRM, move factures → Sales | — | — | Interdit |

## Proposition S1.1

1. Routes Sales pour devis/catalogue **avec** shell Sales (pages partagées ou wrappers)  
2. Hub `/platform/relations` lecture seule sur données existantes  
3. Filtrage Vault « comptable »  
4. Tests parcours Client → Devis → Facture → Envoi inchangé
