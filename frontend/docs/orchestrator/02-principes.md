# 02 — Principes

**P3.0** · Règles officielles ELFIS Orchestrator.

---

## Mantra

```
Orchestrator coordonne. Pilots exécutent.
```

Toute décision de design doit respecter cette phrase.

---

## Règles officielles

| # | Règle | Interdit |
|---|-------|----------|
| R1 | **Owner unique des données** — un seul Pilot possède chaque type d’entité | Deux owners pour la même vérité métier |
| R2 | Chaque Pilot expose **events**, **capabilities**, **actions** | Intégration ad hoc Pilot↔Pilot sans contrat |
| R3 | **Pas de duplication** de logique métier entre Pilots / Orchestrator | Re-coder les règles de facturation dans l’Orchestrator |
| R4 | **Aucune logique métier** dans l’Orchestrator | Calculs TVA, scoring CRM, classification Doc « en dur » |
| R5 | Orchestrator **route, enchaîne, autorise, audite** | Orchestrator crée des factures « lui-même » |
| R6 | Les workflows **ne contournent jamais** les droits utilisateur | Action cross-Pilot sans permission du Pilot cible |
| R7 | Un event décrit un **fait**, pas une instruction | Event = « opportunity.won », pas « createClientNow » |
| R8 | Une **action** est demandée à un Pilot compétent | Appeler directement la base d’un autre Pilot |
| R9 | Centraliser les **automations** cross-produit | Hooks dispersés dans chaque Pilot |
| R10 | Traçabilité : chaque enchaînement a un **correlation id** conceptuel | Chaînes silencieuses non auditables |

---

## Séparation des responsabilités

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Command Center  │     │  Orchestrator   │     │     Pilot       │
│ Intention UX    │────►│ Coordination    │────►│ Exécution métier│
│ Search / launch │     │ Events/Workflow │     │ Données + UI    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

| Couche | Fait | Ne fait pas |
|--------|------|-------------|
| Command Center | Exprimer / lancer une intention | Appliquer règles métier |
| Orchestrator | Matcher event → workflow ; appeler actions ; vérifier droits | Posséder les entités métier |
| Pilot | CRUD métier, validation, UI Product Shell | Orchestrer N Pilots en cascade |

---

## Owner des données (exemples)

| Entité | Owner |
|--------|-------|
| Opportunité / Prospect | SalesPilot |
| Client (fiche commerciale) | SalesPilot *(ou contrat partagé documenté)* |
| Facture / écriture | ComptaPilot |
| Document / classification | DocPilot |
| Employé / contrat RH | HR Pilot |
| Organisation / membres | ELFIS Core (platform) |
| Index de recherche | Search Engine |

Si deux Pilots ont besoin de la même notion, l’un est **owner**, l’autre **consomme** via events / références — pas de copie divergente.

---

## Contrat d’exposition Pilot (résumé)

Chaque Pilot déclare conceptuellement :

```
Pilot
├── Name / Mission
├── Inputs          (ce qu’il accepte)
├── Outputs         (ce qu’il produit)
├── Events          (faits émis)
├── Actions         (opérations invocables)
├── Permissions     (droits requis)
└── Dependencies    (autres Pilots / Core)
```

Détail : [05-pilot-contract.md](./05-pilot-contract.md).

---

## Anti-patterns

| Anti-pattern | Pourquoi refusé |
|--------------|-----------------|
| « God Orchestrator » qui sait tout faire | Couplage monolithe |
| Sync directe Sales → Compta sans event | Contournement du hub |
| Workflow qui ignore le refus d’un Pilot | Contournement des droits |
| Payload event = dump DB complet | Fuite / couplage fort |
| Automatisation dans le frontend d’un seul Pilot pour 3 produits | Non centralisé, non auditable |

---

## Décisions de design

1. **Events d’abord** — le langage commun avant les workflows complexes.  
2. **Actions explicites** — l’Orchestrator demande ; le Pilot valide et exécute.  
3. **Human-in-the-loop** quand le risque / la conformité l’exige.  
4. **Idempotence conceptuelle** — rejouer un event ne doit pas créer le chaos (géré côté Pilot).  
5. **Évolutivité** — nouveaux Pilots se branchent via le contrat, sans rewriter le hub.
