# 11 — Exemples d’intégration entre Pilots

**ELFIS Platform Blueprint V1**

---

## Principe d’exposition minimale

Un Pilot **expose le minimum** nécessaire pour que les autres s’enrichissent.  
Il n’ouvre pas tout son schéma interne.  
Le consommateur **n’administre pas** le domaine de l’émetteur.

---

## Cas 1 — Inventory → Compta

### Inventory expose

| Capacité | Contenu minimal |
|----------|-----------------|
| Catalogue | id article, libellé, unité |
| Prix | prix de vente / grilles autorisées |
| Stock | quantité disponible (et éventuellement réservée) |
| Disponibilité | statut (actif, rupture…) |

### Compta consomme

- Sélection d’article en ligne de facture / devis fiscal
- Affichage du stock pour information
- Prix suggéré

### Compta ne fait **pas**

- Inventaire physique
- Mouvements d’entrepôt
- Deuxième catalogue « local Inventory »

```
Inventory (owner stock)
    │ expose catalogue / prix / stock
    ▼
ComptaPilot (owner facture)
    │ consomme
    ▼
Ligne de facture référence article Inventory
```

---

## Cas 2 — Sales → Compta

### Sales expose

| Capacité | Contenu minimal |
|----------|-----------------|
| Devis accepté | id, relation, lignes, montant |
| Intent `invoice.create` | payload contractuel via Orchestrator |

### Compta consomme

- Création de la **facture fiscale** (owner Compta)
- Lien de traçabilité vers l’opportunité / devis

### Sales ne fait **pas**

- Émettre la facture définitive directement
- Posséder le statut fiscal de la facture

Aligné : [`../domain-separation/01-domain-ownership-matrix.md`](../domain-separation/01-domain-ownership-matrix.md)

---

## Cas 3 — Banking → Compta

### Banking expose

| Capacité | Contenu minimal |
|----------|-----------------|
| Connexion | statut, compte masqué |
| Mouvements | montant, date, libellé, id |

### Compta consomme

- Rapprochement
- Suggestions d’affectation
- Alerts de trésorerie (éventuellement via widgets / Aura)

### Compta ne fait **pas**

- Redevenir le coffre-fort des credentials bancaires hors contrat Core/Banking

---

## Cas 4 — Relations (Core) → tous

### Core / Relations expose

- Identité Party / projection Shared Relation
- Coordonnées, rôles, statut global

### Sales / Compta consomment

- Attacher deals / factures à la même identité
- Vues métier (attrs billing ou pipeline) **sans** recréer la fiche

Réf. : [`../domain-separation/19-shared-relations-contract.md`](../domain-separation/19-shared-relations-contract.md)

---

## Cas 5 — Widget Framework (transverse UI)

Le Widget Framework n’est **pas** un Pilot. C’est une **capacité UI** Core / partagée :

- Compta (FCC) consomme le framework pour présenter des métriques **owned** Compta / Banking.
- Un futur Pilot Sales peut réutiliser la coquille sans hériter du vert Compta.

Réf. : [`../comptapilot/financial-command-center/04-widget-framework.md`](../comptapilot/financial-command-center/04-widget-framework.md)

---

## Matrice rapide

| Émetteur | Capacité | Consommateur | Interdit au consommateur |
|----------|----------|--------------|--------------------------|
| Inventory | catalogue, prix, stock | Compta, Sales | Gérer le stock |
| Sales | devis accepté, intent facture | Compta | Facture fiscale owner Sales |
| Banking | mouvements | Compta | Double ledger bancaire fantôme |
| Relations | identité | Tous | Fiches clonées divergentes |
| Compta | facture / solde | Sales, Aura | Édition fiscale hors Compta |

---

## Synthèse

> **Exposer peu, clairement, contractuellement.**  
> **Consommer sans absorber.**  
> Inventory expose le stock ; Compta ne le gère pas.
