# ELFIS Platform Blueprint V1

| Champ | Valeur |
|-------|--------|
| **Statut** | **Référence officielle** — architecture fondatrice |
| **Version** | V1 |
| **Nature** | Documentation uniquement (phase P0) |
| **Document consolidé** | [14-platform-blueprint-v1.md](./14-platform-blueprint-v1.md) |

Ce dossier constitue le **document fondateur officiel** de la plateforme ELFIS.  
Toute décision d’architecture, d’ownership, d’intégration entre Pilots ou de règles de développement doit s’y aligner.

---

## Document consolidé (entrée principale)

→ **[14 — Platform Blueprint V1 (référence unique)](./14-platform-blueprint-v1.md)**

Synthèse complète : vision, Trois Lois, Zero ressaisie / Zero verrou, capacités, couches, ownership, UX, règles de développement, glossaire et roadmap.

---

## Chapitres

| # | Document | Sujet |
|---|----------|-------|
| 01 | [Vision plateforme](./01-platform-vision.md) | ELFIS = plateforme d’entreprise ; Pilots autonomes ; intelligence croisée |
| 02 | [Trois Lois](./02-three-laws.md) | Autonomie · Enrichissement · Un seul propriétaire |
| 03 | [Architecture progressive](./03-progressive-pilot-architecture.md) | Activation progressive des Pilots |
| 04 | [Zero ressaisie](./04-zero-reentry.md) | Jamais resaisir une donnée déjà connue |
| 05 | [Zero verrou](./05-zero-lock.md) | Activer / désactiver sans perte |
| 06 | [Capacités](./06-capabilities.md) | Capacités vs modules ; exemples Compta → Inventory / Sales / Banking |
| 07 | [Couches plateforme](./07-platform-layers.md) | Core · Pilots · Aura (pas un Pilot) |
| 08 | [Ownership des données](./08-data-ownership.md) | Qui possède quoi |
| 09 | [Principes de design](./09-design-principles.md) | Une seule plateforme ; Design System ; nav ; widgets ; raccourcis |
| 10 | [Règles de développement](./10-development-rules.md) | Checklist avant chaque dev |
| 11 | [Exemples d’intégration](./11-example-integrations.md) | Exposition minimale entre Pilots |
| 12 | [Roadmap architecture](./12-roadmap.md) | Suite après P0 (pas d’implémentation ici) |
| 13 | [Glossaire](./13-glossary.md) | Termes officiels |
| 14 | [Blueprint consolidé V1](./14-platform-blueprint-v1.md) | **Référence unique** |

---

## Travaux déjà engagés (alignement)

Le Blueprint **ne contredit pas** ces chantiers documentés ; il les positionne comme fondations déjà amorcées :

| Domaine | Index / docs |
|---------|----------------|
| Séparation des domaines & ownership | [`../domain-separation/`](../domain-separation/README.md) |
| Shared Relations (S1.2) | [`../domain-separation/19-shared-relations-contract.md`](../domain-separation/19-shared-relations-contract.md) |
| Contrats plateforme / ownership | [`../platform-contracts/`](../platform-contracts/README.md) |
| Expérience plateforme (shell, launcher, nav) | [`../platform/`](../platform/README.md) |
| Widget Framework & Financial Command Center | [`../comptapilot/financial-command-center/`](../comptapilot/financial-command-center/README.md) · [`04-widget-framework.md`](../comptapilot/financial-command-center/04-widget-framework.md) |
| ELFIS Insight Framework (F1.2.5) | [`../insight-framework/`](../insight-framework/README.md) — présentation ; pas de calcul métier |
| Smart Search & Universal Pickers (P1.0) | [`../platform-search/`](../platform-search/README.md) — capacité Core ; Search Engine V1 inchangé |
| Brand — Platform vs Product | [`../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md`](../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md) |

---

## Portée P0

- ✅ Documentation fondatrice complète
- ❌ Aucun développement fonctionnel
- ❌ Aucune modification moteur / API / table / logique métier
- ❌ Pas de S1.3 fonctionnel
- ❌ Pas de Facturation Premium dans cette phase

**Après P0 :** le chantier Facturation Premium peut reprendre (hors scope de ce dossier).

---

## Lecture recommandée

1. [14-platform-blueprint-v1.md](./14-platform-blueprint-v1.md) — vue d’ensemble
2. [02-three-laws.md](./02-three-laws.md) — lois non négociables
3. [10-development-rules.md](./10-development-rules.md) — checklist quotidienne
4. [13-glossary.md](./13-glossary.md) — vocabulaire partagé
