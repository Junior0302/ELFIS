# 01 — Capability Registry

**P3.0.1** · Contrat officiel.  
Capability = **action métier** qu’un Pilot expose à la plateforme.

---

## Définition

```
Capability = ce qu’un Pilot peut faire pour un acteur autorisé
             (pas une route, pas une API, pas un bouton UI)
```

| Est une capability | N’est pas une capability |
|--------------------|--------------------------|
| `invoice.create` | Un écran React |
| `lead.convert` | Un endpoint HTTP |
| `document.classify` | Un event (`invoice.created`) |
| `ticket.assign` | Une Intent utilisateur |

Règle : l’utilisateur **n’appelle jamais** une capability directement → voir [02-intent-model.md](./02-intent-model.md).

---

## Anatomie conceptuelle (obligatoire)

Chaque capability documente **conceptuellement** :

| Champ | Rôle |
|-------|------|
| **Identifiant** | `objet.action` (stable) |
| **Owner** | Pilot responsable de l’exécution |
| **Description** | Une phrase métier |
| **Prérequis** | Contexte / entités / états requis |
| **Permissions** | Droits Pilot requis pour l’acteur |
| **Events émis** | Faits produits en cas de succès (typiques) |
| **Events consommés** | Faits qui peuvent déclencher / enrichir (si applicable) |
| **Résultat attendu** | Outcome métier (succès / refus / échec conceptuels) |

```
┌─────────────────────────────────────────────┐
│              CAPABILITY                     │
│  id · owner · description                   │
│  prérequis · permissions                    │
│  events émis · events consommés             │
│  résultat attendu                           │
└─────────────────────────────────────────────┘
         ▲                        │
         │ sélection              │ exécution
    Orchestrator               Pilot owner
```

---

## Catalogue conceptuel — ComptaPilot

| Capability | Description | Prérequis | Permissions (concept) | Events émis | Events consommés | Résultat attendu |
|------------|-------------|-----------|----------------------|-------------|------------------|------------------|
| `invoice.create` | Créer une facture | Org active ; client référencé | droits facturation création | `invoice.created` | — | Facture créée (ou UI guidée) |
| `invoice.send` | Envoyer une facture | Facture existante, état envoyable | droits facturation envoi | `invoice.sent` | — | Facture marquée envoyée |
| `invoice.cancel` | Annuler une facture | Facture existante, annulable | droits facturation annulation | `invoice.cancelled` | — | Facture annulée |
| `invoice.export` | Exporter une / des factures | Sélection valide | droits facturation lecture / export | — (ou export métier local) | — | Export produit |
| `customer.create` | Créer un client (domaine Compta) | Org active ; données minimales | droits clients création | `customer.created` | évent. refs Sales | Client créé |

---

## Catalogue conceptuel — SalesPilot

| Capability | Description | Prérequis | Permissions (concept) | Events émis | Events consommés | Résultat attendu |
|------------|-------------|-----------|----------------------|-------------|------------------|------------------|
| `lead.create` | Créer un prospect / lead | Org active | droits sales lead | `lead.created` | — | Lead créé |
| `lead.convert` | Convertir un lead | Lead existant, convertible | droits sales conversion | `lead.converted` | — | Lead converti (opportunité / suite) |
| `opportunity.create` | Créer une opportunité | Org ; contexte commercial | droits opportunité création | `opportunity.created` | — | Opportunité créée |
| `opportunity.win` | Marquer opportunité gagnée | Opportunité ouverte | droits opportunité écriture | `opportunity.won` | — | Opportunité gagnée → workflows possibles |
| `proposal.create` | Créer un devis / proposition | Org ; cible commerciale | droits devis création | `proposal.created` | — | Devis créé |

---

## Catalogue conceptuel — DocPilot

| Capability | Description | Prérequis | Permissions (concept) | Events émis | Events consommés | Résultat attendu |
|------------|-------------|-----------|----------------------|-------------|------------------|------------------|
| `document.import` | Importer un document | Org ; source valide | droits doc import | `document.imported` | — | Document importé |
| `document.classify` | Classer un document | Document existant | droits doc classification | `document.classified` | `document.imported` | Classe assignée |
| `document.share` | Partager un document | Document existant ; cible autorisée | droits doc partage | `document.shared` | — | Partage effectif |

---

## Catalogue conceptuel — SupportPilot

| Capability | Description | Prérequis | Permissions (concept) | Events émis | Events consommés | Résultat attendu |
|------------|-------------|-----------|----------------------|-------------|------------------|------------------|
| `ticket.create` | Ouvrir un ticket | Org ; sujet minimal | droits support création | `ticket.created` | — | Ticket ouvert |
| `ticket.assign` | Assigner un ticket | Ticket ouvert ; agent valide | droits support assignation | `ticket.assigned` | — | Ticket assigné |
| `ticket.close` | Clôturer un ticket | Ticket closable | droits support clôture | `ticket.closed` | — | Ticket fermé |

---

## Règles Registry

| # | Règle |
|---|-------|
| C1 | Toute capability a **un seul owner** Pilot |
| C2 | Identifiant stable `objet.action` — pas de camelCase ni d’événements déguisés |
| C3 | Capability = **demande d’action** ; Event = **fait accompli** |
| C4 | Permissions évaluées **dans le Pilot owner** — Orchestrator ne contourne pas |
| C5 | Nouveau Pilot → publier ses capabilities **avant** intégration (voir gouvernance) |
| C6 | Capability absente du registry = **non invocable** via Orchestrator / CC |

---

## Anti-patterns

| Interdit | Pourquoi |
|----------|----------|
| Capability sans owner | Ambiguïté d’exécution |
| Capability qui « orchestre » d’autres Pilots | Rôle Orchestrator |
| Capability = dump CRUD base étrangère | Violation ownership |
| Capability sans permissions documentées | Contournement sécurité |
