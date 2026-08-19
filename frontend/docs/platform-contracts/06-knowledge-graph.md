# 06 — Knowledge Graph

**P3.0.1** · Contrat officiel.  
Le graphe relie les entités par **références** — il **ne stocke pas** les données métier.

---

## Définition

```
Knowledge Graph = relations + navigation + contexte
                ≠ base métier
                ≠ dump Pilot
```

| Stocke | Ne stocke pas |
|--------|---------------|
| Liens typés entre refs | Fiches client / facture / document |
| Type de relation | Montants, lignes, contenu fichier |
| Métadonnées de lien légères | Secrets, permissions métier complètes |
| Pointeurs vers owners | Seconde vérité des domaines |

Owners des nœuds métier : voir [05-ownership-model.md](./05-ownership-model.md).

---

## Chaîne relationnelle de référence

```
Entreprise (Core)
    │
    ├──► Client (ComptaPilot)
    │         │
    │         ├──► Factures (ComptaPilot)
    │         │         │
    │         │         └──► Paiements (ComptaPilot)
    │         │
    │         ├──► Documents (DocPilot)  [liés]
    │         │
    │         └──► Support / Tickets (SupportPilot)
    │
    ├──► Prospects (SalesPilot)
    │         │
    │         ├──► Opportunités / Devis
    │         └──► (conversion) ──► Client
    │
    └──► Historique (events / corrélations — journal + liens)
```

---

## Concepts gelés

| Concept | Définition |
|---------|------------|
| **Relation** | Lien sémantique typé entre deux (ou plus) refs d’entités |
| **Lien** | Instance concrète d’une relation (A → B) |
| **Navigation** | Parcours UX / produit le long des liens (sans changer d’owner) |
| **Traversal** | Parcours programmatique / Orchestrator / IA le long du graphe |
| **Contexte** | Sous-graphe utile à une Intent / un agent (voisins pertinents) |

```
Nœud = référence (id + type + owner)
Arête = relation typée
Graphe ≠ contenu des nœuds
```

---

## Types de relations (exemples conceptuels)

| Relation | De → Vers | Signification |
|----------|-----------|---------------|
| `org.has_customer` | Entreprise → Client | Client de l’org |
| `customer.has_invoice` | Client → Facture | Factures du client |
| `invoice.has_payment` | Facture → Paiement | Paiements liés |
| `entity.has_document` | Client/Facture/… → Document | Pièce jointe / dossier |
| `customer.has_ticket` | Client → Ticket | Support lié |
| `lead.converts_to` | Prospect → Client / Opportunité | Conversion commerciale |
| `opportunity.related_to` | Opportunité → Client / Devis | Pipeline |
| `event.correlates` | Fait → chaîne Intent/Workflow | Historique |

Les noms ci-dessus sont **conceptuels** pour le graphe — distincts des events `objet.action`.

---

## Règles

| # | Règle |
|---|-------|
| G1 | Toute arête pointe vers des **refs owner**, pas vers des copies |
| G2 | Création / MAJ de lien souvent **consécutive à un event** |
| G3 | Suppression / archivage métier → mise à jour des liens (pas de fantômes silencieux) |
| G4 | Traversal respecte les **permissions** des owners pour le détail |
| G5 | Le graphe peut répondre « qui est lié à quoi » ; le métier répond « quel est le contenu » |
| G6 | Orchestrator peut s’appuyer sur le graphe pour **contexte** de workflow — pas pour écrire le métier |

---

## Navigation & Traversal

```
Point d’entrée (ref)
    │
    ▼
Voisins (relations)
    │
    ├─► Navigation UX → deep-link Pilot owner
    ├─► Traversal Orchestrator → contexte workflow
    └─► Traversal IA (futur) → contexte restreint + permissions
```

| Mode | Produit | Garde-fou |
|------|---------|-----------|
| Navigation | Ouverture fiche dans Pilot owner | Droits lecture owner |
| Traversal plateforme | Découverte de liens | Pas d’écriture métier |
| Contexte Intent | Sous-graphe minimal | Corrélation + org |

---

## Préparation IA (conceptuel)

| Principe | Détail |
|----------|--------|
| Graphe = mémoire relationnelle | Aide l’IA à situer les entités |
| Pas de bypass ownership | L’IA lit le détail via owners + permissions |
| Contexte borné | Sous-graphe pertinent, pas crawl illimité |
| Events alimentent | Les faits `objet.action` mettent à jour les liens |
| Intent NL future | Graphe enrichit l’Intent — ne la remplace pas |

```
Intent / question
    │
    ▼
Contexte graphe (refs + relations)
    │
    ▼
Lectures autorisées chez owners
    │
    ▼
Réponse / capability — toujours via Orchestrator
```

---

## Anti-patterns

| Interdit | Motif |
|----------|-------|
| Stocker la facture dans le graphe | Double vérité |
| Lien sans type | Navigation inutile |
| Traversal qui écrit chez un non-owner | Violation ownership |
| Graphe = bus d’instructions | Confusion avec events / capabilities |
