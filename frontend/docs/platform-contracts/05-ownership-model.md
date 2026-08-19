# 05 — Ownership Model

**P3.0.1** · Contrat **le plus important**.  
Un domaine de données = **un seul owner**. Pas de double vérité.

---

## Mantra

```
Un domaine → un owner.
Orchestrator ne possède aucune donnée métier.
Pilots exécutent et détiennent.
ELFIS Core détient le socle plateforme.
```

---

## Registre d’ownership (officiel)

| Domaine | Owner unique | Ne possède pas |
|---------|--------------|----------------|
| **Entreprise / Organisation** | ELFIS Core | Fiches métier Pilot |
| **Membres / rôles plateforme** | ELFIS Core | Droits métier Pilot |
| **Client** | ComptaPilot | Copie Sales divergente |
| **Prospect / Lead** | SalesPilot | Client compta |
| **Opportunité** | SalesPilot | Facture |
| **Devis / Proposition** | SalesPilot | — |
| **Facture** | ComptaPilot | — |
| **Paiement** | ComptaPilot | — |
| **Document** | DocPilot | Contenu « caché » dans un autre Pilot |
| **Ticket support** | SupportPilot | — |
| **Employé (RH)** | HR Pilot *(si présent)* | Compte plateforme (Core) |
| **Index de recherche** | Search Engine | Vérité métier |
| **Relations / liens graphe** | Knowledge Graph (refs) | Données métier |
| **Journal events / workflows** | Orchestrator *(infra)* | Entités métier |

```
ELFIS Core          → Entreprise, membres plateforme
ComptaPilot         → Client, Facture, Paiement
SalesPilot          → Prospect, Opportunité, Devis
DocPilot            → Document
SupportPilot        → Ticket
HR Pilot            → Employé
Search Engine       → Index (dérivé)
Knowledge Graph     → Relations (références)
Orchestrator        → Coordination seulement
```

---

## Orchestrator : frontières

| Orchestrator **peut** | Orchestrator **ne peut pas** |
|----------------------|------------------------------|
| Router Intent → Capability | Créer / modifier une facture « lui-même » |
| Enchaîner des actions Pilot | Stocker la fiche client |
| Journaliser events / corrélations | Devenir second owner d’un domaine |
| Vérifier préconditions de plateforme | Recalculer TVA / scoring / classification |
| Auditer les chaînes | Contourner un refus du Pilot owner |

```
┌──────────────┐     demande action      ┌─────────────┐
│ Orchestrator │ ───────────────────────►│ Pilot owner │
│ (coordonne)  │ ◄──── résultat/event ───│ (détient)   │
└──────────────┘                         └─────────────┘
```

---

## Matrice d’opérations

Légende : **O** = owner · **L** = lecture autorisée (si permission) · **R** = référencement (lien / id) · **I** = interdit

| Domaine | Owner | Autre Pilot lecture | Autre Pilot écriture | Orchestrator | Search | Knowledge Graph |
|---------|-------|---------------------|----------------------|--------------|--------|-----------------|
| Entreprise | Core | L (contexte) | I (sauf Core) | R / contexte | L index | R |
| Client | Compta | L si permission | **I** (sauf Compta) | R via capability | L index | R |
| Prospect | Sales | L si permission | **I** | R via capability | L index | R |
| Facture | Compta | L si permission | **I** | R via capability | L index | R |
| Paiement | Compta | L si permission | **I** | R via capability | L index | R |
| Document | Doc | L si permission | **I** | R via capability | L index | R |
| Ticket | Support | L si permission | **I** | R via capability | L index | R |

---

## Règles par opération

### Lecture

| Règle | Détail |
|-------|--------|
| L1 | Lecture cross-Pilot **via permissions du owner** |
| L2 | Préférer refs + demande ciblée plutôt que cache divergente |
| L3 | Search lit l’**index**, pas la base métier d’un autre Pilot |

### Écriture

| Règle | Détail |
|-------|--------|
| W1 | **Seul l’owner** écrit la vérité du domaine |
| W2 | Autre Pilot → demande capability / event → owner exécute |
| W3 | Orchestrator **demande** ; n’écrit jamais le métier |

### Référencement

| Règle | Détail |
|-------|--------|
| R1 | Stocker un **id / lien** vers l’entité owner = autorisé |
| R2 | Stocker une **copie mutable** de la fiche owner = interdit |
| R3 | Knowledge Graph = références et types de liens uniquement |

### Suppression

| Règle | Détail |
|-------|--------|
| D1 | Suppression métier = capability owner |
| D2 | Cascade cross-Pilot = workflow Orchestrator + actions owners |
| D3 | Interdit : supprimer « en silence » les refs d’autrui sans event |

### Archivage

| Règle | Détail |
|-------|--------|
| A1 | Archivage = responsabilité owner (politique métier) |
| A2 | Events d’archivage si impacts cross-produit |
| A3 | Graph / Search mettent à jour les **refs / index**, pas l’archive métier |

---

## Conflits & partage

| Situation | Résolution |
|-----------|------------|
| Deux Pilots « ont besoin » du même concept | Un owner ; l’autre **consomme** (L / R) |
| Notion ambiguë (ex. « client commercial » vs « client compta ») | Domaines distincts ou owner unique documenté ici |
| Doute | **NO GO** jusqu’à clarification gouvernance (07) |

---

## Anti-patterns

| Interdit | Motif |
|----------|-------|
| Double owner Client | Divergence de vérité |
| Orchestrator table « clients » | Violation mantra |
| Sync bidirectionnelle silencieuse | Chaos + non-audit |
| Copie complète fiche pour « perf » sans contrat | Divergence garantie |
| Écriture dans la base d’un autre Pilot | Contournement ownership |
