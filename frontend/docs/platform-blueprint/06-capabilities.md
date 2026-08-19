# 06 — Capacités (pas modules)

**ELFIS Platform Blueprint V1**

---

## Modules vs capacités

| Approche | Idée | Problème / limite |
|----------|------|-------------------|
| **Modules** | Gros blocs couplés (« module stock dans Compta ») | Couplage fort, double ownership, Zero ressaisie cassé |
| **Capacités** | Contrats d’exposition ciblés qu’un Pilot **offre** aux autres | Couplage faible, Loi 2 respectée |

> ELFIS raisonne en **capacités exposées / consommées**, pas en « modules empilés dans un monolithe ».

---

## Définition

Une **capacité** est une surface contractuelle (API, intent, événement, projection lecture) qu’un Pilot (ou le Core) **expose** pour qu’un autre acteur puisse :

- lire une information owned ailleurs ;
- demander une action à l’owner ;
- s’abonner à un événement ;

…**sans devenir propriétaire** du domaine.

---

## Exemples — Compta consomme

| Capacité (owner) | Ce que Compta peut faire | Ce que Compta ne fait pas |
|------------------|--------------------------|---------------------------|
| **Catalogue / prix / stock** (Inventory) | Sélectionner un article, afficher stock dispo, prix de vente | Gérer les mouvements de stock, inventaires, entrepôts |
| **Pipeline / devis accepté** (Sales) | Recevoir un intent de facturation, lier une opportunité | Devenir le CRM, éditer le pipeline |
| **Connexion / transactions** (Banking) | Rapprocher, suggérer affectations | Remplacer le service bancaire / possession des connexions hors contrat |

```
Inventory ──expose──► catalogue, prix, stock disponible
Sales      ──expose──► devis accepté, intent invoice.create
Banking    ──expose──► mouvements, statut connexion
     │
     ▼
ComptaPilot ──consomme──► sans absorber ces domaines
```

---

## Exemples — Compta expose

| Capacité Compta | Consommateurs typiques |
|-----------------|------------------------|
| Facture émise / statut | Sales (suivi), Aura (alertes) |
| Solde client (billing) | Relations / vues métier |
| Écritures / clôture (selon droits) | Reporting, Aura |

---

## Principes de design des capacités

1. **Minimale** — exposer le nécessaire, pas le schéma interne entier.
2. **Versionnable** — contrats stables (voir platform-contracts).
3. **Orientée intention** — préférer intents / événements à du « SQL partagé ».
4. **Respect ownership** — lecture large possible ; écriture = owner.
5. **Optionnelle** — absence de capacité = dégradation gracieuse (Loi 1).

---

## Alignement repo

- Intent model & ownership — [`../platform-contracts/`](../platform-contracts/README.md)
- Orchestrator (Pilot → Orchestrator → Pilot) — [`../domain-separation/README.md`](../domain-separation/README.md) (règle 5)
- Widget Framework comme capacité **UI transversale** (coquille, pas métier) — [`../comptapilot/financial-command-center/04-widget-framework.md`](../comptapilot/financial-command-center/04-widget-framework.md)

---

## Capacités Core — Smart Search & Universal Pickers (P1.0)

Le Core expose deux capacités UX transversales (pas un Pilot) :

| Capacité | Rôle | Owner technique |
|----------|------|-----------------|
| **Smart Search** | Contrats `SearchResult` / scopes / UI combobox ; fuzzy = **Search Engine V1** | Core (`frontend/src/platform-search/`) |
| **Universal Pickers** | Relation / Customer / Supplier / Document / Product — consomment Smart Search | Core |

Les Pilots **consomment** ces pickers (ex. Document Composer → `CustomerPicker`) sans recréer un moteur de recherche.  
Détail : [`../platform-search/`](../platform-search/README.md)

---

## Capacité transversale — ELFIS Resource System (F1.2)

| Capacité | Rôle | Owner technique |
|----------|------|-----------------|
| **ELFIS Resource System / Smart Library** | Abstraction `ResourceSource` + UI bibliothèque ; Local Library aujourd’hui, InventoryPilot demain | Core (`frontend/src/resource-library/`) + consommation ComptaPilot |

- **ProductPicker** est le premier consommateur officiel (Document Composer étape produits).
- Les écrans ne connaissent **pas** la source concrète hors adapters.
- Remplacement Local → Inventory : zero UX change / zero ressaisie (voir [`../resource-library/08-inventory-ready.md`](../resource-library/08-inventory-ready.md)).

Détail : [`../resource-library/`](../resource-library/README.md)

---

## Capacité transversale — ELFIS Insight Framework (F1.2.5)

| Capacité | Rôle | Owner technique |
|----------|------|-----------------|
| **ELFIS Insight Framework** | Contrat `Insight` + UI de présentation (alertes, conseils, validations, opportunités…) ; mappers depuis données existantes — **pas** de calcul métier | Core (`frontend/src/insight-framework/`) |

- **Widgets** = containers ; **Insights** = contenu signal présenté.
- Indépendant des Pilots ; confiance / source affichées **uniquement si fournies**.
- Premiers consommateurs : Financial Command Center + Document Composer (validation).

Détail : [`../insight-framework/`](../insight-framework/README.md)

---

## Synthèse

> On n’ajoute pas un « module stock dans Compta ».  
> On **consomme la capacité stock** d’Inventory.  
> Compta reste Compta.
