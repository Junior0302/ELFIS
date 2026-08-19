# 07 — Couches de la plateforme

**ELFIS Platform Blueprint V1**

---

## Vue d’ensemble

ELFIS s’organise en **trois couches**. Elles ne sont pas interchangeables.

```
┌─────────────────────────────────────────────┐
│  Couche 3 — Aura                            │
│  Intelligence transversale (pas un Pilot)   │
├─────────────────────────────────────────────┤
│  Couche 2 — Pilots                          │
│  Expertises métier autonomes                │
├─────────────────────────────────────────────┤
│  Couche 1 — ELFIS Core                      │
│  Socle plateforme, données & services       │
│  partagés                                   │
└─────────────────────────────────────────────┘
```

---

## Couche 1 — ELFIS Core

**Rôle :** socle commun à toute organisation.

| Domaine Core (indicatif) | Exemples |
|--------------------------|----------|
| Identité & accès | Org, membres, rôles plateforme |
| Shell & navigation | Topbar, launcher, search, notifs |
| Relations / Party (projection → modèle unifié futur) | Identité clients / fournisseurs / contacts |
| Documents (Vault) | Stockage partagé |
| Communications | E-mail transactionnel, canaux |
| Contrats / Orchestrator (infra) | Intents, events, coordination |
| Design System | Tokens, composants UI officiels |

Core **ne remplace pas** la compta ni le CRM. Il **porte** ce qui est multi-Pilot.

Docs liés : [`../platform/`](../platform/README.md) · [`../domain-separation/`](../domain-separation/README.md)

---

## Couche 2 — Pilots

**Rôle :** expertises métier **activables**, soumises aux Trois Lois.

### Liste de référence (architecture)

| Pilot / famille | Domaine | Statut architecture |
|-----------------|---------|---------------------|
| **ComptaPilot** | Facturation fiscale, comptabilité, finance | Actif (produit) |
| **SalesPilot** | Pipeline, devis, intelligence commerciale | Actif (produit) |
| **Inventory** | Catalogue, stock, prix | Cible / capacité future |
| **Banking** | Connexions bancaires, flux | Services / vue ; ownership à respecter |
| **Doc / Vault surfaces métier** | Documents métier filtrés | Partagé Core + vues |
| Autres (Support, HR…) | Selon roadmap | Prospectifs |

Cette liste est **architecturale**. Elle **ne crée pas** de nouveau Pilot dans cette phase P0.

---

## Couche 3 — Aura

**Rôle :** couche d’**intelligence** et d’assistance transversale.

| Aura **est** | Aura **n’est pas** |
|--------------|--------------------|
| Assistante / copilote plateforme | Un Pilot métier |
| Lectrice de signaux multi-Pilot | Owner de factures, deals, stock |
| Source de priorités, alertes, aide | Un silo de données métier parallèle |
| Présente au niveau plateforme (ex. `/platform/aura`) | Un produit concurrent des Pilots |

Règle d’or : **Aura enrichit l’expérience ; elle ne possède pas les domaines.**

Alignement migration Aura — [`../domain-separation/13-aura-migration.md`](../domain-separation/13-aura-migration.md) (si présent dans l’index domain-separation).

---

## Interactions entre couches

```
UI Pilot  →  capacités / intents  →  Orchestrator / contrats  →  Pilot owner
UI Pilot  →  lecture Core (Relations, org, vault)
Aura      →  lecture agrégée (signaux)  →  suggestions / deep-links
```

Jamais : Pilot A écrit en silence dans les tables de Pilot B.

---

## Synthèse

> **Core** porte le commun.  
> **Pilots** portent l’expertise.  
> **Aura** porte l’intelligence — **sans être un Pilot**.
