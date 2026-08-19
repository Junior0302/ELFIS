# 09 — Roadmap Orchestrator

**P3.0** · Trajectoire produit (documentation).  
**P3.1+** non démarrée ici.

---

## Vue d’ensemble

```
V1 Events
  │
  ▼
V2 Workflows
  │
  ▼
V3 Automation
  │
  ▼
V4 AI commands
  │
  ▼
V5 Supervised autonomous agents
```

Chaque version **s’appuie** sur la précédente ; pas de saut vers des agents sans events / droits solides.

---

## V1 — Events

| Livrable conceptuel | Description |
|---------------------|-------------|
| Catalogue d’events | Langage commun (voir 03) |
| Émission Pilot → hub | Faits métier standardisés |
| Journal / correlation | Traçabilité de base |
| Listeners simples | Notify, Search reindex, Analytics |

**Hors V1 :** moteurs de workflow complexes, IA, agents.

**Critère de succès :** un Pilot peut publier un fait ; un autre peut réagir sans couplage direct.

---

## V2 — Workflows

| Livrable conceptuel | Description |
|---------------------|-------------|
| Définition de workflows | Déclencheurs + étapes + gates |
| Invocation d’actions Pilot | Contrat 05 |
| Statuts run | pending / running / awaiting / completed / failed |
| Scénarios phares | Prospect gagné, facture payée, etc. |

**Critère de succès :** un event déclenche un enchaînement multi-Pilot **avec** respect des droits.

---

## V3 — Automation

| Livrable conceptuel | Description |
|---------------------|-------------|
| Règles org | Activer / désactiver workflows par organisation |
| Schedules / conditions | Déclencheurs temporels ou seuils |
| Politiques | Qui peut éditer les automations |
| Observabilité | Taux d’échec, files d’attente conceptuelles |

**Critère de succès :** l’admin configure des automations sans coder dans chaque Pilot.

---

## V4 — AI commands

| Livrable conceptuel | Description |
|---------------------|-------------|
| Intention depuis langage naturel | CC → interpréteur → intention structurée |
| Même contrat permissions | L’IA n’élève pas les droits |
| Clarification | `needs_input` si ambigu |
| Suggestions | Proposer un workflow, pas l’exécuter en silence |

```
NL → AI → intention → Orchestrator → Pilot
              │
              └── audit identique aux commandes manuelles
```

**Critère de succès :** une commande IA emprunte le même chemin sécurisé qu’une commande explicite.

---

## V5 — Agents autonomes supervisés

| Livrable conceptuel | Description |
|---------------------|-------------|
| Agents bornés | Mission + périmètre Pilot / org |
| Supervision humaine | Gates obligatoires sur actions à risque |
| Proposition → validation | Jamais d’autonomie totale sur finance / ACL |
| Kill switch | Coupure org-wide des agents |

```
Agent propose plan
    │
    ▼
Orchestrator (simule / estime)
    │
    ▼
Humain valide
    │
    ▼
Exécution Pilot(s) + audit
```

**Critère de succès :** gain d’autonomie **sans** perte de contrôle ni contournement des frontières 08.

---

## Alignement phases projet

| Phase doc / produit | Focus |
|---------------------|--------|
| **P3.0** (cette doc) | Blueprint uniquement |
| **P3.1** (futur) | Premiers fondements techniques events — *ne pas démarrer ici* |
| Ultérieur | Workflows, automations, CC branché, IA |

---

## Dépendances externes

| Dépendance | Notes |
|------------|-------|
| Platform Shell / CC | Porte d’entrée UX déjà en place (P2.4) |
| Search Engine | Index ; pas un orchestrateur |
| Contrats Pilot | Doivent être publiés avant branchage massif |
| ACL Core + Pilot | Prérequis sécurité |

---

## Non-objectifs (toutes versions)

- Remplacer les Pilots  
- Marketplace dans l’Orchestrator  
- Contournement des droits « pour l’IA »  
- Monolithe métier central
