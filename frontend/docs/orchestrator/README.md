# ELFIS Orchestrator — Blueprint P3.0

**Statut :** documentation officielle  
**Portée :** blueprint uniquement — **aucun code / route / backend / React**.  
**Suite :** P3.1 — (hors scope de ce dossier ; ne pas démarrer ici).

---

## Définition

**ELFIS Orchestrator** est le **chef d’orchestre** de la plateforme ELFIS Core. Il coordonne les interactions entre Pilots (ComptaPilot, SalesPilot, DocPilot, HR, etc.) sans les remplacer : les Pilots restent propriétaires de leur métier et exécutent les actions ; l’Orchestrator centralise les événements, les workflows et les automatisations cross-produit.

> Orchestrator coordonne. Pilots exécutent.

---

## Index

| # | Document | Contenu |
|---|----------|---------|
| 01 | [Vision](./01-vision.md) | Pourquoi l’Orchestrator existe ; flux utilisateur → résultat |
| 02 | [Principes](./02-principes.md) | Règles officielles (owner, events, no métier dans Orchestrator) |
| 03 | [Modèle d’événements](./03-event-model.md) | Langage commun d’events (émetteurs, listeners, payloads conceptuels) |
| 04 | [Modèle de workflows](./04-workflow-model.md) | Concept workflow + scénarios ASCII |
| 05 | [Contrat Pilot](./05-pilot-contract.md) | Contrat Pilot ↔ Orchestrator |
| 06 | [Scénarios cross-produit](./06-cross-product-scenarios.md) | Interactions entre Pilots (sans implémentation) |
| 07 | [Contrat Command Center](./07-command-center-contract.md) | Comment le CC dialogue avec l’Orchestrator |
| 08 | [Frontières de sécurité](./08-security-boundaries.md) | Droits, audit, validation humaine, rollback |
| 09 | [Roadmap](./09-roadmap.md) | V1 Events → V5 Agents supervisées |

---

## Vocabulaire (aligné plateforme)

| Terme | Rôle |
|-------|------|
| **ELFIS Core** | Plateforme : session, org, chrome commun |
| **Platform Shell** | Cadre UI commun (topbar, launcher, search, notif, profil) |
| **Pilot** | Produit métier indépendant (Compta, Sales, Doc, HR…) |
| **Product Shell** | Cadre UI du Pilot actif |
| **App Launcher** | Grille de bascule entre Pilots |
| **Command Center** | Point d’entrée universel (rechercher, naviguer, lancer) |
| **Orchestrator** | Conducteur cross-Pilot (événements, workflows, automations) |

---

## Hors scope P3.0

| Exclu | Motif |
|-------|--------|
| Code, routes, APIs, backend | Phase documentation |
| Nouveaux Pilots | Non créé ici |
| Modifications Command Center / Search Engine / Platform Shell | Docs plateforme inchangées |
| Implémentation workflows / events | → phases ultérieures (P3.1+) |
| Agents IA autonomes | Roadmap V4–V5 uniquement (concept) |
| Marketplace, Theme Engine | Hors Orchestrator |

---

## Relation avec les docs existantes

Ce dossier **complète** `frontend/docs/platform/` (expérience shell / CC / launcher).  
Il ne remplace ni le Brand Book, ni les specs Pilot individuelles.
