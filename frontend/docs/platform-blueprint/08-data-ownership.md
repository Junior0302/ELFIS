# 08 — Ownership des données

**ELFIS Platform Blueprint V1**

---

## Mantra

```
Une donnée → un propriétaire.
Les autres lisent ou demandent.
Personne ne devient co-owner silencieux.
```

---

## Registre Blueprint V1 (cible architecture)

| Domaine de données | Propriétaire | Notes |
|--------------------|--------------|-------|
| **Entreprise / Organisation** | **ELFIS Core** | Membres, rôles plateforme, settings org |
| **Clients / Parties (identité, rôles)** | **Relations (Core)** | Projection Shared Relations aujourd’hui ; Party unifié = suite (S1.3+) |
| **Produits / catalogue / stock** | **Inventory** | Compta & Sales consomment ; n’owns pas le stock |
| **Paiements / connexions bancaires** | **Banking** *(services / domaine bancaire)* | Compta consomme pour rapprochement & écritures liées selon contrats |
| **Comptabilité / factures fiscales / écritures** | **ComptaPilot** | Vérité fiscale & comptable |
| **Pipeline / opportunités / devis commerciaux** | **SalesPilot** | Avant facture définitive |

> Les intitulés **Inventory** et **Banking** désignent des **domaines d’ownership** cibles du Blueprint. Leur maturité produit peut être partielle ; cela n’autorise pas Compta ou Sales à s’approprier ces domaines.

---

## Compléments (déjà documentés dans le repo)

Pour le détail opérationnel (routes, tables, risques), se référer à :

| Doc | Rôle |
|-----|------|
| [`../domain-separation/01-domain-ownership-matrix.md`](../domain-separation/01-domain-ownership-matrix.md) | Matrice objets S1 |
| [`../platform-contracts/05-ownership-model.md`](../platform-contracts/05-ownership-model.md) | Contrat ownership officiel P3 |
| [`../domain-separation/19-shared-relations-contract.md`](../domain-separation/19-shared-relations-contract.md) | Frontière Core vs attrs Sales / Compta |

Le Blueprint **ne contredit pas** ces matrices : il les **survole** au niveau plateforme. En cas de détail d’implémentation, les docs domain-separation / platform-contracts font foi pour l’état courant du code.

---

## Règles d’écriture

| Acteur | Peut |
|--------|------|
| Owner | Créer / modifier / archiver dans son domaine |
| Autre Pilot | Lire via capacité ; déclencher intent vers l’owner |
| Orchestrator | Router, journaliser, enchaîner — **pas** posséder |
| Aura | Suggérer, alerter — **pas** écrire la vérité métier |

---

## Exemple de flux ownership

```
Prospect / deal     → SalesPilot (owner)
Devis accepté       → SalesPilot
intent invoice.create → Orchestrator
Facture fiscale     → ComptaPilot (owner)
Paiement / banque   → Banking (+ écriture Compta selon contrat)
Document PDF        → Vault / Doc (Core)
Identité client     → Relations (Core)
```

SalesPilot **ne crée pas** la facture définitive directement (aligné domain-separation).

---

## Anti-patterns

| Anti-pattern | Correction |
|--------------|------------|
| Deux tables « client » divergentes sans projection | Shared Relations / Party |
| Compta qui stocke le stock | Capacité Inventory |
| Aura qui « corrige » une facture en base | Intent vers Compta |
| Copie de fiche à chaque déplacement d’UI | Déplacer la vue, pas la donnée |

---

## Synthèse

| | Owner |
|--|-------|
| Entreprise | Core |
| Clients (identité) | Relations |
| Produits | Inventory |
| Paiements (bancaire) | Banking |
| Comptabilité | Compta |
| Pipeline | Sales |
