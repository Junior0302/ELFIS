# 14 — ELFIS Platform Blueprint V1  
## Document consolidé — référence unique

| Champ | Valeur |
|-------|--------|
| **Statut** | **Référence officielle** |
| **Version** | V1 |
| **Phase** | P0 — architecture fondatrice (documentaire) |
| **Index** | [README.md](./README.md) |

Ce document synthétise l’ensemble du Blueprint. Les chapitres 01–13 détaillent chaque sujet ; en cas de lecture unique, **partir d’ici**.

---

## 1. Vision

**ELFIS est une plateforme d’entreprise**, pas un logiciel métier isolé.

- **Core** porte le commun (organisation, shell, Relations, vault, contrats…).
- **Pilots** sont des expertises **autonomes** et **activables**.
- La différenciation vient de l’**intelligence croisée** : capacités partagées, Zero ressaisie, Aura transversale.
- L’utilisateur ressent **un seul logiciel**.

→ Détail : [01-platform-vision.md](./01-platform-vision.md)

---

## 2. Les Trois Lois

| Loi | Énoncé |
|-----|--------|
| **1 — Autonomie** | Chaque Pilot doit pouvoir fonctionner seul. |
| **2 — Enrichissement** | Un autre Pilot actif enrichit — il n’absorbe pas le domaine. |
| **3 — Un seul propriétaire** | Chaque donnée a un unique owner. |

Exemples : Compta sans Sales ; Inventory enrichit Compta sans que Compta gère le stock ; facture owned Compta, deal owned Sales.

→ Détail : [02-three-laws.md](./02-three-laws.md)

---

## 3. Architecture progressive

On active les Pilots **au fil des besoins** (Core → Pilot primaire → duo/trio → écosystème).  
Pas de big-bang obligatoire. Dégradation gracieuse si une capacité manque.  
Désactivation sûre = Zero verrou.

→ Détail : [03-progressive-pilot-architecture.md](./03-progressive-pilot-architecture.md)

---

## 4. Zero ressaisie

Une info déjà connue **ne se retape pas** ailleurs.  
Lire chez l’owner ; projeter ; référencer par id stable.  
Symptôme inverse = double vérité.

Travaux engagés : Shared Relations / domain-separation (projection avant Party unifié S1.3+).

→ Détail : [04-zero-reentry.md](./04-zero-reentry.md)

---

## 5. Zero verrou

Activer / désactiver un Pilot **sans perte** des données owned.  
Désactivation = retrait d’accès / features, pas destruction.  
Réactivation = reprise sans ressaisie massive.

→ Détail : [05-zero-lock.md](./05-zero-lock.md)

---

## 6. Capacités (pas modules)

ELFIS n’empile pas des « modules » couplés dans un monolithe.  
Chaque Pilot **expose des capacités** minimales ; les autres **consomment**.

Exemple : Compta consomme catalogue / prix / stock (Inventory), intents Sales, mouvements Banking — **sans** gérer stock, CRM ou coffre bancaire.

Le Core expose aussi **Smart Search** et **Universal Pickers** (P1.0) : contrats UX communs branchés sur Search Engine V1 + APIs domaine — sans second moteur.

Le Core expose **ELFIS Resource System / Smart Library** (F1.2) : abstraction `ResourceSource` (Local Library → futur InventoryPilot) + UI bibliothèque ; ProductPicker en est le premier consommateur.

Le Core expose **ELFIS Insight Framework** (F1.2.5) : contrat `Insight` + composants de présentation pour analyses / alertes / recommandations / validations — sans nouveau moteur IA ; FCC et Document Composer en sont les premiers consommateurs.

→ Détail : [06-capabilities.md](./06-capabilities.md) · [11-example-integrations.md](./11-example-integrations.md) · [`../platform-search/`](../platform-search/README.md) · [`../resource-library/`](../resource-library/README.md)

---

## 7. Trois couches

```
Couche 3  Aura          → intelligence (PAS un Pilot)
Couche 2  Pilots        → Compta, Sales, Inventory, Banking, Doc…
Couche 1  ELFIS Core    → socle partagé
```

→ Détail : [07-platform-layers.md](./07-platform-layers.md)

---

## 8. Ownership (registre Blueprint)

| Domaine | Owner |
|---------|-------|
| Entreprise | **Core** |
| Clients / identité Parties | **Relations (Core)** |
| Produits / stock | **Inventory** |
| Paiements / banque | **Banking** |
| Comptabilité / factures fiscales | **ComptaPilot** |
| Pipeline / devis commerciaux | **SalesPilot** |

Détail runtime / routes / tables : matrices `domain-separation` & `platform-contracts` (état courant du repo) — le Blueprint ne les contredit pas.

→ Détail : [08-data-ownership.md](./08-data-ownership.md)

---

## 9. Intégration entre Pilots

- Exposition **minimale** et contractuelle.
- Pilot → Orchestrator / contrats → Pilot (pas d’écriture silencieuse croisée).
- Inventory expose ; Compta consomme ; Compta ne gère pas le stock.

→ Détail : [11-example-integrations.md](./11-example-integrations.md)

---

## 10. UX — une sensation de logiciel

- Platform Shell (Core) + Product Shell (Pilot).
- **Design System** unique ; accents Pilot, pas langages UI parallèles.
- Navigation prévisible (launcher, search, deep-links).
- **Widget Framework** pour dashboards (coquille agnostique ; FCC = consommateur V1).
- **Insight Framework** pour présenter alertes / analyses / validations (FCC + Composer = premiers consommateurs).
- Raccourcis plateforme (palette, launcher).

→ Détail : [09-design-principles.md](./09-design-principles.md)

---

## 11. Règles de développement (checklist)

Avant chaque dev :

1. **Propriétaire** clair  
2. **Autonomie** (Loi 1) + dégradation  
3. **Réutilisation** / Zero ressaisie  
4. **Widgets** / Design System / chrome  
5. **Aura** ≠ Pilot ; pas d’écriture métier sauvage  
6. **Trois Lois**  
7. **Zero verrou**

→ Détail : [10-development-rules.md](./10-development-rules.md)

---

## 12. Travaux déjà engagés (citations)

Le Blueprint s’appuie sur ces chantiers **déjà documentés** ; il les officialise au niveau plateforme :

| Chantier | Lien |
|----------|------|
| Séparation des domaines | [`../domain-separation/README.md`](../domain-separation/README.md) |
| Shared Relations | [`../domain-separation/19-shared-relations-contract.md`](../domain-separation/19-shared-relations-contract.md) |
| Ownership contracts | [`../platform-contracts/05-ownership-model.md`](../platform-contracts/05-ownership-model.md) |
| Expérience plateforme | [`../platform/README.md`](../platform/README.md) |
| Widget Framework / FCC | [`../comptapilot/financial-command-center/04-widget-framework.md`](../comptapilot/financial-command-center/04-widget-framework.md) |
| Insight Framework | [`../insight-framework/`](../insight-framework/README.md) |
| Platform vs Product | [`../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md`](../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md) |

---

## 13. Roadmap (architecture)

- **P0 terminée** (ce Blueprint).
- **Facturation Premium** peut reprendre **après** P0 (non démarrée ici).
- **S1.3 Relations** = suite future (Party unifié) ; pas dans P0.
- Pas de dates irréalistes ; priorité = respecter le Blueprint sur tout nouveau chantier.

→ Détail : [12-roadmap.md](./12-roadmap.md)

---

## 14. Glossaire

Pilot · Core · Aura · capacité · ownership · Widget Framework · Insight Framework · Zero ressaisie · Zero verrou · Intent · Orchestrator · Platform / Product Shell…

→ Détail : [13-glossary.md](./13-glossary.md)

---

## Portée P0 — rappel

| Fait | Non fait (interdit P0) |
|------|-------------------------|
| Documentation fondatrice complète | Moteurs / API / tables / logique métier |
| Référence officielle V1 | Nouveau Pilot |
| Liens vers docs existants | S1.3 fonctionnel |
| | Facturation Premium (reprise **après**) |

---

## Phrase de clôture

> **ELFIS = plateforme. Pilots = expertises autonomes. Capacités = intégration. Un owner = une vérité. Une UX = un logiciel.**
