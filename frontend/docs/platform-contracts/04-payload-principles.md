# 04 — Payload Principles

**P3.0.1** · Contrat officiel.  
Principes de contenu des payloads — **sans JSON, sans schéma technique, sans API**.

---

## But

Un payload transporte le **minimum utile** pour router, auditer et corréler.  
Le détail métier reste chez le **Pilot owner**.

```
Event / message
├── Identité & provenance
├── Contexte plateforme
├── Références objet
└── Métadonnées légères
        │
        ▼
Listener a besoin du détail ?
        │
        └──► demande au Pilot owner (lecture autorisée)
```

---

## Contenu conceptuel obligatoire / typique

| Élément | Rôle | Règle |
|---------|------|-------|
| **Id** | Identifiant unique du fait / message | Toujours présent |
| **Organisation** | Isolation multi-tenant | Toujours présent |
| **Auteur** | Acteur humain ou système à l’origine | Présent si applicable |
| **Horodatage** | Moment du fait | Toujours présent |
| **Version** | Version du contrat de payload (conceptuelle) | Présente et évolutive avec prudence |
| **Contexte** | Org, Pilot émetteur, canal (CC / UI / automation) | Minimal, utile au routage |
| **Objet concerné** | Référence(s) à l’entité métier | IDs / refs — pas l’entité complète |
| **Métadonnées** | Labels utiles au dispatch (type, criticité…) | Pas de dump métier |
| **Corrélation** | Lien Intent / workflow / chaîne | Présent dès qu’il y a enchaînement |

---

## Règles (gelées)

| # | Règle |
|---|-------|
| P1 | **Références > copies** — IDs et liens, pas de clone de fiche |
| P2 | **Pas de secrets** — tokens, mots de passe, clés absents |
| P3 | **Pas d’instruction** — payload = données d’un fait, pas une commande |
| P4 | **Pas de dump DB** — pas de ligne complète ni jointures massives |
| P5 | **Org toujours** — aucun payload « sans organisation » en contexte multi-tenant |
| P6 | **Corrélation** — toute chaîne Orchestrator porte une corrélation conceptuelle |
| P7 | **Version** — évolution additive préférée ; rupture = nouveau contrat documenté |
| P8 | **Besoin de détail** → lecture chez l’owner, jamais enrichissement silo divergents |

---

## Ce qui entre / ce qui sort

| Inclure | Exclure |
|---------|---------|
| Id du fait | Entité métier complète |
| Type / nom `objet.action` | Secrets / PII non nécessaires au routage |
| Org | Instructions (« crée client ») |
| Refs objet (ex. id facture, id client) | Blobs documents |
| Auteur + horodatage | Historique complet |
| Corrélation + version | État UI / session browser |

---

## Matrice par usage

| Usage | Contenu attendu |
|-------|-----------------|
| Dispatch Orchestrator | Type, org, refs, corrélation |
| Audit | Id, auteur, horodatage, org, corrélation |
| Knowledge Graph | Refs + type de relation (pas le métier) |
| Search (réindex) | Refs + signaux minimaux pour l’index |
| Notify | Refs + libellés non sensibles |

---

## Cycle conceptuel

```
Pilot émet fait
    │  payload minimal
    ▼
Orchestrator
    │  journal · match workflow · corrélation
    ▼
Listeners / autres Pilots
    │  si besoin détail → lecture owner
    ▼
Knowledge Graph (liens) / Search (refs) / Notify
```

---

## Anti-patterns

| Interdit | Motif |
|----------|-------|
| Payload = « toute la facture » | Couplage + fuite |
| Payload sans org | Rupture isolation |
| Payload avec secrets | Sécurité |
| Payload impératif | Confusion event / capability |
| Payload sans Id / horodatage | Non auditable |
| Schéma JSON figé dans ce contrat | Hors scope P3.0.1 |
