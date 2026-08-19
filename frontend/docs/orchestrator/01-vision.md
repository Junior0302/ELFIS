# 01 — Vision

**P3.0** · Pourquoi ELFIS Orchestrator existe.

---

## Problème

ELFIS Core regroupe plusieurs Pilots (Compta, Sales, Doc, HR…). Sans chef d’orchestre :

- chaque Pilot invente ses propres « hooks » cross-produit ;
- les automatisations se dupliquent et divergent ;
- Command Center ne peut lancer que des navigations locales ;
- l’utilisateur doit enchaîner manuellement les étapes métier.

L’Orchestrator apporte un **point unique de coordination** sans fusionner les produits.

---

## Pourquoi l’Orchestrator existe

| Besoin | Réponse Orchestrator |
|--------|----------------------|
| Enchaîner des actions multi-Pilot | Workflows centralisés |
| Notifier les autres produits d’un fait métier | Bus d’événements commun |
| Lancer une intention depuis Command Center | Routage vers le Pilot compétent |
| Garder une trace cross-produit | Audit / corrélation |
| Éviter N×N intégrations Pilot↔Pilot | Hub : Pilot ↔ Orchestrator uniquement |

```
        ┌─────────────┐
        │ Orchestrator│
        └──────┬──────┘
   ┌───────────┼───────────┐
   ▼           ▼           ▼
Compta      Sales        Doc …
```

---

## Pourquoi chaque Pilot reste indépendant

| Principe | Conséquence |
|----------|-------------|
| **Owner unique des données** | Compta possède factures ; Sales possède opportunités |
| **Métier dans le Pilot** | Règles comptables / CRM / RH restent locales |
| **Évolutions découplées** | Un Pilot peut versionner sans bloquer les autres |
| **Permissions natives** | Les droits métier restent ceux du Pilot |
| **UI Product Shell** | Chaque Pilot garde son identité et sa navigation |

L’Orchestrator **n’est pas** un super-Pilot ni un monolithe métier.

---

## Pourquoi centraliser les automatisations

Sans centralisation :

```
Sales ──hook──► Compta
Sales ──hook──► Doc
Compta──hook──► Analytics
Doc   ──hook──► Compta
… (explosion N×N)
```

Avec Orchestrator :

```
Pilot ──event──► Orchestrator ──workflow──► Pilot(s)
```

Avantages : un seul endroit pour définir / auditer / désactiver une automation ; cohérence org-wide ; Command Center et futures commandes IA s’appuient sur la même couche.

---

## Flux de référence

```
Utilisateur
    │
    ▼
Command Center          (intention : chercher / naviguer / lancer)
    │
    ▼
Orchestrator            (résout : quel Pilot ? quel workflow ? droits ?)
    │
    ▼
Pilot                   (exécute l’action métier)
    │
    ▼
Résultat                (entité créée / statut / notification / event)
```

Exemple conceptuel — « Créer une facture » :

```
User → CC → Orchestrator → ComptaPilot → Facture créée → Event invoice.created
```

Exemple conceptuel — « Prospect gagné » :

```
User (Sales) → sales.opportunity.won → Orchestrator → workflow
                 ├─► Sales : créer / lier client
                 ├─► Compta : dossier client
                 ├─► Doc : dossier documents
                 └─► Notify + Analytics
```

---

## Position dans ELFIS Core

```
┌────────────────────────────────────────────────────┐
│ Platform Shell (chrome, session, org)              │
│  Launcher · Command Center · Search · Notif        │
├────────────────────────────────────────────────────┤
│              ELFIS ORCHESTRATOR                    │
│         events · workflows · routing               │
├──────────┬──────────┬──────────┬───────────────────┤
│ Compta   │ Sales    │ Doc      │ HR · …            │
│ Pilot    │ Pilot    │ Pilot    │ Pilots            │
└──────────┴──────────┴──────────┴───────────────────┘
```

Search Engine indexe ; Command Center exprime l’intention ; Orchestrator **orchestre** ; Pilots **exécutent**.
