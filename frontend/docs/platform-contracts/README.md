# ELFIS — Contrats Plateforme (P3.0.1)

**Statut :** officiel · longévité multi-années  
**Portée :** documentation uniquement — **aucun code / JSON / API / backend / React**.  
**Suite :** P3.1 — hors scope ; ne pas démarrer ici.

---

## Définition

Les **contrats plateforme** figent les règles que **tous les Pilots** (présents et futurs) doivent respecter pour s’intégrer à ELFIS Core.

> Les contrats **figent les règles**.  
> Les docs Orchestrator (P3.0) donnent la **vision** et le blueprint.

```
Orchestrator Blueprint (P3.0)     →  « pourquoi / comment ça s’enchaîne »
Platform Contracts (P3.0.1)       →  « ce qui est obligatoire pour toujours »
```

---

## Backbone officiel

```
Utilisateur
    │
    ▼
Command Center          (exprime une Intent — jamais une capability brute)
    │
    ▼
Intent                  (intention structurée)
    │
    ▼
Orchestrator            (sélectionne capability · orchestre · audite)
    │
    ▼
Capability              (action métier déclarée)
    │
    ▼
Pilot                   (exécute · possède les données métier)
    │
    ▼
Event                   (fait objet.action)
    │
    ▼
Knowledge Graph         (relations / références — pas de dump métier)
    │
    ▼
Autres Pilots           (consomment via Orchestrator · refs · events)
```

Mantra aligné P3.0 :

```
Orchestrator coordonne. Pilots exécutent.
```

---

## Vocabulaire (aligné)

| Terme | Rôle |
|-------|------|
| **ELFIS Core** | Socle : session, org, chrome commun |
| **Platform Shell** | Cadre UI commun (topbar, launcher, search, notif) |
| **Command Center** | Point d’entrée universel — Intent UX |
| **Intent** | Intention utilisateur (pas un appel capability direct) |
| **Orchestrator** | Coordination events / workflows / routing |
| **Capability** | Action métier exposée par un Pilot |
| **Pilot** | Produit métier indépendant (owner des données) |
| **Event** | Fait métier nommé `objet.action` |
| **Knowledge Graph** | Graphe de relations / navigation contextuelle |
| **Owner** | Unique responsable d’un domaine de données |

---

## Index des contrats

| # | Document | Ce qu’il fige |
|---|----------|---------------|
| 01 | [Capability Registry](./01-capability-registry.md) | Notion de capability + catalogue conceptuel |
| 02 | [Intent Model](./02-intent-model.md) | Intent → Orchestrator → Capability |
| 03 | [Event Naming](./03-event-naming.md) | Convention `objet.action` + règles |
| 04 | [Payload Principles](./04-payload-principles.md) | Contenu conceptuel des payloads (sans schéma technique) |
| 05 | [Ownership Model](./05-ownership-model.md) | Owner unique par domaine + droits d’accès |
| 06 | [Knowledge Graph](./06-knowledge-graph.md) | Relations, liens, traversal, contexte IA |
| 07 | [Platform Governance](./07-platform-governance.md) | Onboarding Pilot + matrice GO / NO GO |

---

## Relation avec `frontend/docs/orchestrator/`

| Dossier | Nature | Usage |
|---------|--------|-------|
| `orchestrator/` (P3.0) | Vision, principes, scénarios, roadmap | Lire pour comprendre |
| `platform-contracts/` (P3.0.1) | Règles gelées multi-années | **Obligatoire** pour tout Pilot |

En cas de divergence future entre une formulation « vision » et un contrat : **le contrat gagne**.

---

## Hors scope P3.0.1

| Exclu | Motif |
|-------|--------|
| Code, APIs, schémas JSON techniques | Documentation pure |
| Implémentation Orchestrator / Pilots | → P3.1+ |
| Modification des docs Orchestrator | Lecture seule autorisée |
| Invention d’APIs / events techniques non listés | Contrats conceptuels seulement |
| Marketplace, Theme Engine détaillés | Hors contrats (checklist gouvernance seulement) |
