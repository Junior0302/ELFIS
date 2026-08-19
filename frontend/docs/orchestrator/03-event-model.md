# 03 — Modèle d’événements

**P3.0** · Langage commun des faits métier.  
**Aucun code** — payloads conceptuels uniquement.

---

## Concept

Un **event** = un fait qui s’est produit dans un Pilot (ou Core).  
L’Orchestrator l’écoute, le journalise, et peut déclencher des **workflows**.

```
Pilot (émetteur)
    │  emit event
    ▼
Orchestrator
    │  match rules / workflows
    ▼
Pilot(s) listeners  (+ Notify / Analytics)
```

Convention de nommage : `domaine.entité.verbe`  
Ex. `sales.opportunity.won`, `invoice.paid`.

---

## Catalogue (V1 conceptuel)

### Sales

| Event | Émetteur | Listeners typiques | Payload conceptuel |
|-------|----------|--------------------|--------------------|
| `sales.opportunity.created` | SalesPilot | Analytics, Notify | `opportunityId`, `orgId`, `ownerId`, `amount?`, `stage` |
| `sales.opportunity.won` | SalesPilot | Orchestrator→workflow, Compta, Doc, Analytics | `opportunityId`, `orgId`, `customerRef?`, `amount`, `wonAt` |
| `sales.opportunity.lost` | SalesPilot | Analytics, Notify | `opportunityId`, `orgId`, `reason?` |
| `sales.customer.created` | SalesPilot | Compta, Doc, Analytics, Search | `customerId`, `orgId`, `name`, `createdBy` |
| `sales.customer.updated` | SalesPilot | Compta (sync ref), Search | `customerId`, `orgId`, `changedFields` |

### Facturation / Compta

| Event | Émetteur | Listeners typiques | Payload conceptuel |
|-------|----------|--------------------|--------------------|
| `invoice.created` | ComptaPilot | Sales (lien), Doc, Analytics, Search | `invoiceId`, `orgId`, `customerRef`, `amount`, `currency` |
| `invoice.sent` | ComptaPilot | Notify, Sales, Analytics | `invoiceId`, `orgId`, `sentAt`, `channel?` |
| `invoice.paid` | ComptaPilot | Orchestrator→workflow, Bank?, Analytics, Notify | `invoiceId`, `orgId`, `paidAt`, `amount`, `paymentRef?` |
| `invoice.cancelled` | ComptaPilot | Sales, Analytics, Search | `invoiceId`, `orgId`, `reason?` |

### Documents

| Event | Émetteur | Listeners typiques | Payload conceptuel |
|-------|----------|--------------------|--------------------|
| `document.imported` | DocPilot | Orchestrator→workflow, Compta?, Search | `documentId`, `orgId`, `source`, `mime?`, `importedBy` |
| `document.classified` | DocPilot | Compta (si facture), Notify | `documentId`, `orgId`, `class`, `confidence?` |
| `document.linked` | DocPilot | Pilot owner de l’entité liée | `documentId`, `orgId`, `targetType`, `targetId` |

### Banque

| Event | Émetteur | Listeners typiques | Payload conceptuel |
|-------|----------|--------------------|--------------------|
| `bank.transaction.synced` | Compta / Bank module | Compta (rapprochement), Analytics | `txId`, `orgId`, `amount`, `date`, `label?` |
| `bank.transaction.matched` | ComptaPilot | Analytics, Notify | `txId`, `invoiceId?`, `orgId` |

### Organisation / Platform

| Event | Émetteur | Listeners typiques | Payload conceptuel |
|-------|----------|--------------------|--------------------|
| `organization.created` | ELFIS Core | Tous Pilots (provision), Analytics | `orgId`, `name`, `createdBy` |
| `organization.updated` | ELFIS Core | Pilots (contexte), Search | `orgId`, `changedFields` |
| `organization.member.added` | ELFIS Core | Notify, HR?, Pilots (ACL) | `orgId`, `userId`, `role` |
| `user.removed` | ELFIS Core | Tous Pilots (révocation), Audit | `orgId`, `userId`, `removedBy` |

### RH

| Event | Émetteur | Listeners typiques | Payload conceptuel |
|-------|----------|--------------------|--------------------|
| `hr.employee.created` | HR Pilot | Doc (dossier), Compta?, Notify, Core | `employeeId`, `orgId`, `userRef?`, `startDate` |
| `hr.employee.offboarded` | HR Pilot | Core (accès), Doc, Audit | `employeeId`, `orgId`, `endDate` |

---

## Champs communs (conceptuels)

Tout event porte au minimum :

| Champ | Rôle |
|-------|------|
| `eventId` | Identifiant unique du fait |
| `type` | Nom canonique (`invoice.paid`…) |
| `orgId` | Isolation multi-tenant |
| `occurredAt` | Horodatage du fait |
| `emittedBy` | Pilot / service émetteur |
| `actorId?` | Utilisateur à l’origine (si humain) |
| `correlationId?` | Lien à un workflow / commande CC |
| `payload` | Données métier minimales (refs, pas dump) |

---

## Règles payload

```
✓ IDs + références + métadonnées utiles au routage
✗ Copie complète de l’entité
✗ Secrets / tokens
✗ Instructions impératives (« crée X »)
```

Le listener qui a besoin du détail **demande au Pilot owner** via une action / lecture autorisée.

---

## Cycle de vie conceptuel

```
emit → validate (schéma) → persist journal → dispatch listeners
                                              │
                                              ├─ sync handlers (critiques)
                                              └─ async workflows
```

Échec d’un listener : journalisé ; ne corrompt pas l’event source (politique de retry / DLQ = phases ultérieures).
