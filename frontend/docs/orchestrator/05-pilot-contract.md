# 05 — Contrat Pilot ↔ Orchestrator

**P3.0** · Interface officielle pour brancher un Pilot.

---

## Contrat (champs obligatoires)

| Champ | Description |
|-------|-------------|
| **Name** | Identifiant produit (ex. `ComptaPilot`) |
| **Mission** | Raison d’être métier en une phrase |
| **Inputs** | Données / commandes acceptées |
| **Outputs** | Entités / résultats produits |
| **Events** | Faits émis vers l’Orchestrator |
| **Actions** | Opérations invocables par l’Orchestrator / CC |
| **Permissions** | Droits requis pour chaque action |
| **Dependencies** | Autres Pilots / Core / Search |

```
┌──────────────────────────────────────────┐
│                 PILOT                    │
│  Name · Mission                          │
│  Inputs ──────────────► métier interne   │
│  Outputs / Events ────► Orchestrator     │
│  Actions ◄───────────── Orchestrator/CC  │
│  Permissions · Dependencies              │
└──────────────────────────────────────────┘
```

Règle : **aucune action n’est exécutable** si la permission Pilot correspondante est absente pour l’acteur.

---

## Pilots principaux (conceptuel)

### ComptaPilot

| Champ | Contenu |
|-------|---------|
| Mission | Comptabilité, facturation, rapprochements |
| Inputs | Clients (refs), documents classés, paiements, commandes CC |
| Outputs | Factures, écritures, dossiers compta, statuts paiement |
| Events | `invoice.*`, `bank.transaction.matched`, … |
| Actions | `invoice.create`, `invoice.send`, `customer.dossier.ensure`, `payment.record` |
| Permissions | `compta.invoice.*`, `compta.read`, `compta.admin` |
| Dependencies | Core (org/user), Doc (pièces), Sales (refs client), Search |

### SalesPilot

| Champ | Contenu |
|-------|---------|
| Mission | Pipeline commercial, prospects, clients commerciaux |
| Inputs | Leads, interactions, commandes CC, events paiement |
| Outputs | Opportunités, clients Sales, activités |
| Events | `sales.opportunity.*`, `sales.customer.*` |
| Actions | `opportunity.create`, `opportunity.mark_won`, `customer.create`, `customer.link` |
| Permissions | `sales.*` |
| Dependencies | Core, Compta (facturation liée), Doc, Search |

### DocPilot

| Champ | Contenu |
|-------|---------|
| Mission | Import, classification, stockage, liaison documents |
| Inputs | Fichiers, métadonnées, demandes de dossier |
| Outputs | Documents, classes, liens vers entités |
| Events | `document.imported`, `document.classified`, `document.linked` |
| Actions | `document.import`, `document.classify`, `folder.ensure`, `document.link` |
| Permissions | `doc.*` |
| Dependencies | Core, Compta/Sales/HR (cibles de liaison), Search |

### HR Pilot (conceptuel)

| Champ | Contenu |
|-------|---------|
| Mission | Cycle de vie employés / onboarding |
| Inputs | Fiches employé, contrats, événements org |
| Outputs | Employés, offboarding |
| Events | `hr.employee.created`, `hr.employee.offboarded` |
| Actions | `employee.create`, `employee.offboard` |
| Permissions | `hr.*` |
| Dependencies | Core (comptes), Doc, éventuellement Compta |

### ELFIS Core (platform)

| Champ | Contenu |
|-------|---------|
| Mission | Session, organisations, membres, chrome |
| Inputs | Auth, admin org |
| Outputs | Org, membres, rôles plateforme |
| Events | `organization.*`, `user.removed`, `organization.member.added` |
| Actions | `org.provision_member`, `org.revoke_member` |
| Permissions | `platform.admin`, rôles org |
| Dependencies | — (socle) |

### Analytics / Notify (services transverses)

| Service | Rôle face à l’Orchestrator |
|---------|----------------------------|
| **Notify** | Listener d’events / étapes workflow → notifications Platform Shell |
| **Analytics** | Listener best-effort pour métriques |
| **Search Engine** | Réindexation suite aux events (owner index ≠ métier) |

---

## Matrice Actions × Permissions (extrait)

| Action | Pilot | Permission minimale |
|--------|-------|---------------------|
| `invoice.create` | Compta | `compta.invoice.create` |
| `invoice.send` | Compta | `compta.invoice.send` |
| `customer.create` | Sales | `sales.customer.create` |
| `opportunity.mark_won` | Sales | `sales.opportunity.write` |
| `document.import` | Doc | `doc.import` |
| `folder.ensure` | Doc | `doc.write` |
| `employee.create` | HR | `hr.employee.create` |
| `org.revoke_member` | Core | `platform.admin` (ou équivalent) |

---

## Cycle d’invocation

```
Orchestrator
   │  request action (actor, org, params)
   ▼
Pilot
   │  1. authz (permissions)
   │  2. validate métier
   │  3. execute
   │  4. emit event(s)
   ▼
Résultat (ok | denied | failed) + eventId?
```

`denied` n’est **pas** contournable par le workflow.

---

## Onboarding d’un nouveau Pilot

1. Remplir le contrat (table ci-dessus).  
2. Publier la liste d’events / actions.  
3. Déclarer les permissions.  
4. Brancher les listeners / workflows nécessaires.  
5. Documenter les owners de données (pas de double vérité).

Aucun Pilot n’est créé dans P3.0 — ce document fixe seulement le **contrat**.
