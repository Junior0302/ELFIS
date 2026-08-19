# 06 — Scénarios cross-produit

**P3.0** · Interactions uniquement — **jamais** de détail d’implémentation.

---

## Comment lire

Chaque scénario décrit : déclencheur → acteurs → enchaînement → résultat attendu côté utilisateur.  
Les flèches passent par l’**Orchestrator** sauf lecture pure UI dans un seul Pilot.

---

## 1. Prospect gagné

**But :** transformer une opportunité gagnée en présence client cross-produit.

```
SalesPilot
  └─ opportunity.won
        │
        ▼
   Orchestrator
        ├─► Sales   : client commercial create/link
        ├─► Compta  : dossier compta client
        ├─► Doc     : dossier documents
        ├─► Notify  : équipe commerciale
        └─► Analytics : conversion
```

| Acteur | Interaction |
|--------|-------------|
| Sales | Émet le fait « gagné » ; assure la fiche client |
| Orchestrator | Enchaîne les actions selon droits |
| Compta / Doc | Préparent l’espace métier sans que Sales les appelle en direct |

---

## 2. Facture payée

**But :** propager le paiement aux parties prenantes.

```
ComptaPilot
  └─ invoice.paid
        │
        ▼
   Orchestrator
        ├─► Sales    : maj statut / activité liée
        ├─► Doc      : pièce / tag archivage
        ├─► Notify   : confirmation
        └─► Analytics: encaissement
```

Pas de contournement : si l’utilisateur n’a pas accès Sales, la maj Sales est **denied** ou exécutée sous un service autorisé documenté (politique org) — jamais en silence total sans audit.

---

## 3. Document importé

**But :** classer et router vers le Pilot compétent.

```
User / dépôt
  └─► DocPilot : import
        └─ document.imported
              │
              ▼
         Orchestrator
              ├─► Doc : classify
              │     └─ document.classified
              ▼
         Orchestrator (selon classe)
              ├─ facture?  → Compta (brouillon / revue)
              ├─ contrat?  → Doc link + Notify
              └─ RH?       → HR / Doc dossier
```

Validation humaine si confiance faible ou impact financier.

---

## 4. Nouvel employé

**But :** onboarding cross-produit cohérent.

```
HR Pilot
  └─ employee.created
        │
        ▼
   Orchestrator
        ├─► Core : accès / rôle (si compte)
        ├─► Doc  : dossier RH
        ├─► Compta : fiche liée (si module)
        └─► Notify : manager + checklist
```

---

## 5. Nouvelle organisation

**But :** provisionner le terrain de jeu des Pilots.

```
ELFIS Core
  └─ organization.created
        │
        ▼
   Orchestrator
        ├─► Core     : config de base
        ├─► Compta   : espace compta vide / defaults
        ├─► Sales    : pipeline initial?
        ├─► Doc      : coffre org
        └─► Notify   : admin org
```

Chaque Pilot **s’initialise lui-même** ; l’Orchestrator ordonne et vérifie le succès.

---

## 6. Suppression / retrait utilisateur

**But :** révoquer l’accès partout sans laisser d’orphelins de droits.

```
ELFIS Core
  └─ user.removed  (org scope)
        │
        ▼
   Orchestrator
        ├─► Core   : session / membership
        ├─► Compta : révoquer ACL Pilot
        ├─► Sales  : révoquer ACL Pilot
        ├─► Doc    : révoquer ACL Pilot
        ├─► HR     : offboard lié si besoin
        └─► Audit  : trace complète
```

Critique sécurité : **aucune étape ne peut être skippée** pour « aller plus vite ». Échec partiel → statut `failed` + alerte admin.

---

## Matrice scénarios × Pilots

| Scénario | Sales | Compta | Doc | HR | Core | Notify |
|----------|:-----:|:------:|:---:|:--:|:----:|:------:|
| Prospect gagné | ● | ● | ● | | | ● |
| Facture payée | ○ | ● | ○ | | | ● |
| Document importé | | ○ | ● | ○ | | ○ |
| Nouvel employé | | ○ | ● | ● | ● | ● |
| Nouvelle org | ○ | ○ | ○ | ○ | ● | ● |
| User removed | ● | ● | ● | ○ | ● | ○ |

● = acteur principal · ○ = participant conditionnel

---

## Règles transverses

1. Toujours passer par Orchestrator pour le cross-produit.  
2. Toujours respecter les permissions du Pilot cible.  
3. Toujours journaliser (correlationId).  
4. Préférer les **références** aux copies de données.  
5. Prévoir une issue utilisateur (Notify / CC) en cas d’échec d’étape critique.
