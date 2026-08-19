# 01 — Vision plateforme

**ELFIS Platform Blueprint V1** · Chapitre fondateur

---

## ELFIS n’est pas un logiciel métier isolé

ELFIS est une **plateforme d’entreprise**.

Elle unifie, autour d’une organisation, les expertises métier (comptabilité, commercial, stock, banque, documents…) sans forcer l’utilisateur à jongler entre des outils cloisonnés ni à recréer les mêmes données partout.

```
Organisation
    └── ELFIS (plateforme)
            ├── Socle commun (Core)
            ├── Pilots (expertises autonomes)
            └── Aura (intelligence transversale)
```

---

## Les Pilots sont autonomes

Un **Pilot** est une application métier spécialisée, **activable** selon les besoins de l’entreprise.

| Caractéristique | Signification |
|-----------------|---------------|
| Autonome | Peut fonctionner sans les autres Pilots |
| Spécialisé | Possède un domaine et une expertise clairs |
| Intégré | Enrichit / consomme des capacités d’autres Pilots quand ils sont actifs |
| Non obligatoire | L’absence d’un Pilot ne casse pas la plateforme |

Exemples de famille (cible architecture — certains existent déjà, d’autres sont prospectifs) :

- **ComptaPilot** — facturation, comptabilité, finance
- **SalesPilot** — pipeline, devis, intelligence commerciale
- **Inventory** (cible) — catalogue, stock, prix
- **Banking** (cible / services) — connexions bancaires, flux
- **Doc / Vault** — documents partagés
- Autres Pilots selon la roadmap produit

---

## Intelligence croisée

La valeur d’ELFIS ne se limite pas à la somme des Pilots. Elle vient de l’**intelligence croisée** :

1. Chaque Pilot **expose** un minimum de capacités utiles aux autres.
2. Chaque Pilot **consomme** les données du propriétaire légitime — sans les recopier.
3. **Aura** orchestre une compréhension transversale (assistance, priorités, alertes) **sans devenir un Pilot métier**.
4. L’utilisateur perçoit **une seule plateforme**, pas une mosaïque d’apps.

```
Compta lit le stock (Inventory) sans gérer le stock
Sales lit le client (Relations / Core) sans être le CRM « copy »
Aura lit les signaux de plusieurs Pilots sans les posséder
```

---

## Ce que la vision interdit

| Interdit | Pourquoi |
|----------|----------|
| Un « monolithe métier » unique | Rigidifie, empêche l’activation progressive |
| Des silos étanches sans contrats | Force la ressaisie et les doubles vérités |
| Qu’Aura possède des données métier | Contredit ownership et Trois Lois |
| Qu’un Pilot copie le domaine d’un autre | Double vérité, dette, Zero ressaisie cassé |

---

## Alignement avec les travaux déjà engagés

Cette vision s’aligne sur :

- Séparation des domaines — [`../domain-separation/`](../domain-separation/README.md)
- Contrats plateforme & ownership — [`../platform-contracts/`](../platform-contracts/README.md)
- Expérience « plateforme d’abord » — [`../platform/01-experience-principles.md`](../platform/01-experience-principles.md)
- Brand Platform vs Product — [`../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md`](../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md)

---

## Synthèse

> **ELFIS = plateforme d’entreprise.**  
> **Les Pilots = expertises autonomes, activables.**  
> **L’intelligence croisée = la différenciation.**  
> **Une sensation : un seul logiciel.**
