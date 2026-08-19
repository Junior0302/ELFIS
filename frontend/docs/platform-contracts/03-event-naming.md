# 03 — Event Naming

**P3.0.1** · Contrat officiel.  
Tout event plateforme suit **`objet.action`**.

---

## Convention gelée

```
objet.action
```

| Correct | Incorrect |
|---------|-----------|
| `invoice.created` | `InvoiceCreated` |
| `invoice.sent` | `newInvoice` |
| `invoice.paid` | `InvoiceEvent` |
| `proposal.accepted` | `PROPOSAL_ACCEPTED` |
| `lead.converted` | `sales.lead.convert` *(capability, pas event)* |
| `customer.created` | `onCustomerCreate` |
| `document.imported` | `doc.import.done` |
| `organization.updated` | `orgUpdate` |

---

## Catalogue de référence (non exhaustif)

| Event | Objet | Action (fait) | Émetteur typique |
|-------|-------|---------------|------------------|
| `invoice.created` | invoice | created | ComptaPilot |
| `invoice.sent` | invoice | sent | ComptaPilot |
| `invoice.paid` | invoice | paid | ComptaPilot |
| `invoice.cancelled` | invoice | cancelled | ComptaPilot |
| `proposal.accepted` | proposal | accepted | SalesPilot |
| `proposal.created` | proposal | created | SalesPilot |
| `lead.created` | lead | created | SalesPilot |
| `lead.converted` | lead | converted | SalesPilot |
| `opportunity.created` | opportunity | created | SalesPilot |
| `opportunity.won` | opportunity | won | SalesPilot |
| `customer.created` | customer | created | ComptaPilot |
| `document.imported` | document | imported | DocPilot |
| `document.classified` | document | classified | DocPilot |
| `document.shared` | document | shared | DocPilot |
| `ticket.created` | ticket | created | SupportPilot |
| `ticket.assigned` | ticket | assigned | SupportPilot |
| `ticket.closed` | ticket | closed | SupportPilot |
| `organization.updated` | organization | updated | ELFIS Core |
| `organization.created` | organization | created | ELFIS Core |

---

## Règles de nommage

| # | Règle | Détail |
|---|-------|--------|
| E1 | **Format** | Exactement `objet.action` — un point, deux segments |
| E2 | **Temps** | Participe passé / état accompli (`created`, `sent`, `paid`) — **pas** l’impératif |
| E3 | **Singulier** | `invoice`, `customer`, `document` — jamais `invoices.created` |
| E4 | **minuscules** | ASCII lowercase uniquement |
| E5 | **Verbes** | Actions métier stables ; éviter jargon technique (`syncedOk`, `handlerRan`) |
| E6 | **Préfixes** | **Interdits** hors contrat : `on*`, `new*`, `do*`, namespaces camelCase |
| E7 | **Capability ≠ Event** | `invoice.create` (demande) ≠ `invoice.created` (fait) |
| E8 | **Fait, pas instruction** | Event décrit ce qui s’est passé — jamais « crée X maintenant » |
| E9 | **Un fait = un nom** | Pas de fourre-tout `invoice.event` |

```
Capability (demande)          Event (fait)
invoice.create          →     invoice.created
invoice.send            →     invoice.sent
lead.convert            →     lead.converted
```

---

## Versioning

| Pratique | Règle |
|----------|-------|
| Évolution compatible | Ajouter des champs payload conceptuels **optionnels** — **ne pas** renommer l’event |
| Changement sémantique | Nouveau nom `objet.action` — ne pas réutiliser l’ancien sens |
| Version dans le nom | **Interdit** (`invoice.created.v2`) — versionner le **contrat payload**, pas le nom |
| Alias | Un seul nom canonique ; pas de synonymes officiels |

---

## Dépréciation

| Étape | Action |
|-------|--------|
| 1 | Marquer l’event **deprecated** dans le registre conceptuel |
| 2 | Documenter le **successeur** `objet.action` |
| 3 | Période de dual-emit (conceptuelle) si migration Pilots |
| 4 | Retrait après fenêtre de gouvernance (voir 07) |
| 5 | Interdit : réintroduire le même nom avec un autre sens |

---

## Alignement Capability / Event

| Capability | Event succès typique |
|------------|----------------------|
| `invoice.create` | `invoice.created` |
| `invoice.send` | `invoice.sent` |
| `invoice.cancel` | `invoice.cancelled` |
| `customer.create` | `customer.created` |
| `lead.create` | `lead.created` |
| `lead.convert` | `lead.converted` |
| `opportunity.win` | `opportunity.won` |
| `proposal.create` | `proposal.created` |
| `document.import` | `document.imported` |
| `ticket.close` | `ticket.closed` |

---

## Anti-patterns (gelés)

```
✗ InvoiceCreated
✗ newInvoice
✗ InvoiceEvent
✗ invoice_created
✗ invoice:created
✗ sales.opportunity.won.v3
✗ createInvoice (event)
```
