# 04 — Modèle de workflows

**P3.0** · Enchaînements cross-Pilot pilotés par l’Orchestrator.

---

## Concept

Un **workflow** = une procédure déclarée qui réagit à un **déclencheur** (event ou commande CC) et enchaîne des **étapes** : appels d’actions Pilot, notifications, éventuelle validation humaine.

```
Trigger (event | commande CC)
    │
    ▼
Orchestrator Workflow Engine (conceptuel)
    │
    ├─ check permissions (acteur + org)
    ├─ step 1 → Pilot A action
    ├─ step 2 → Pilot B action
    ├─ gate?  → validation humaine
    └─ emit events dérivés / notify
```

L’Orchestrator **ne calcule pas** le métier des étapes ; il **orchestre** l’ordre, les conditions et l’audit.

---

## Anatomie d’un workflow

| Élément | Description |
|---------|-------------|
| `id` / nom | Identifiant stable |
| Déclencheur | Event ou intention Command Center |
| Conditions | Org, droits, flags produit |
| Étapes | Actions Pilot + ordre |
| Gates | Validation humaine optionnelle |
| Compensations | Rollback / annulation conceptuelle |
| Journal | correlationId, statut, erreurs |

États conceptuels : `pending` → `running` → `awaiting_validation` → `completed` | `failed` | `cancelled`.

---

## Scénario A — Prospect gagné

**Déclencheur :** `sales.opportunity.won`

```
[Sales] opportunity.won
        │
        ▼
   Orchestrator
        │
        ├─► [Sales]  assurer fiche client (create/link)
        │              └─ emit sales.customer.created? 
        ├─► [Compta] créer / lier dossier client compta
        ├─► [Doc]    créer dossier documents client
        ├─► [Notify] informer owner + équipe
        └─► [Analytics] enregistrer conversion
```

---

## Scénario B — Facture payée

**Déclencheur :** `invoice.paid`

```
[Compta] invoice.paid
        │
        ▼
   Orchestrator
        │
        ├─► [Sales]  maj statut opportunité / client liée
        ├─► [Doc]    archiver / taguer pièce justificative
        ├─► [Notify] confirmation paiement
        └─► [Analytics] cash-in
```

---

## Scénario C — Document importé puis classifié

**Déclencheur :** `document.imported` puis éventuellement `document.classified`

```
[Doc] document.imported
        │
        ▼
   Orchestrator
        │
        ├─► [Doc]    pipeline classification (action Doc)
        │              └─ emit document.classified
        │
        ▼ (si class = facture fournisseur)
   Orchestrator
        │
        ├─► [Compta] proposer brouillon facture / dépôt
        └─► [Notify] revue humaine si confiance faible
```

---

## Scénario D — Nouvel employé

**Déclencheur :** `hr.employee.created`

```
[HR] employee.created
        │
        ▼
   Orchestrator
        │
        ├─► [Core]   provision accès / rôle (si user lié)
        ├─► [Doc]    dossier RH documents
        ├─► [Compta] fiche paie / coût? (si module)
        └─► [Notify] manager + onboarding
```

---

## Scénario E — Commande depuis Command Center

**Déclencheur :** intention CC « Créer une facture »

```
User → Command Center → Orchestrator
                            │
                            ├─ resolve capability: compta.invoice.create
                            ├─ check permission user
                            └─► [Compta] action create (UI ou API Pilot)
                                    └─ résultat → CC / navigation
```

Voir [07-command-center-contract.md](./07-command-center-contract.md).

---

## Patterns d’enchaînement

| Pattern | Usage |
|---------|--------|
| **Séquence** | Étapes strictes A → B → C |
| **Fan-out** | Une étape déclenche N actions parallèles |
| **Gate humaine** | Pause jusqu’à validation |
| **Compensation** | Annuler / marquer failed les étapes précédentes si possible |
| **Best-effort** | Notify / Analytics peuvent échouer sans bloquer le cœur |

```
Séquence          Fan-out           Gate
A → B → C         A ─┬→ B           A → [✓?] → B
                     └→ C
```

---

## Ce qu’un workflow n’est pas

- Pas un remplacement du Product Shell du Pilot  
- Pas un script SQL cross-bases  
- Pas une permission magique  
- Pas l’endroit pour coder la TVA ou le scoring CRM
