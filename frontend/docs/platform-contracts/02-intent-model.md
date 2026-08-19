# 02 — Intent Model

**P3.0.1** · Contrat officiel.  
L’utilisateur exprime une **Intent** ; jamais une capability brute.

---

## Définition

```
Intent     = ce que l’utilisateur veut obtenir (langage / action UX)
Capability = ce que le Pilot sait exécuter (action métier enregistrée)
```

| Couche | Parle | Ne parle pas |
|--------|-------|--------------|
| Utilisateur / Command Center | Intent | Capability interne, SQL, APIs |
| Orchestrator | Intent → Capability / Workflow | Règles métier Pilot |
| Pilot | Capability + données | Intent UX globale |

---

## Flux officiel

```
Utilisateur
    │  « Créer une facture »
    ▼
Command Center
    │  Intent structurée
    ▼
Orchestrator
    │  1. résoudre Intent
    │  2. sélectionner Capability
    │  3. vérifier contexte / droits (routing)
    │  4. lancer workflow ou action unique
    ▼
Pilot owner
    │  exécute Capability
    ▼
Résultat + Event(s)
```

Mantra :

```
CC exprime. Orchestrator résout. Pilot exécute.
```

---

## Mapping Intent → Capability (exemples)

| Intent (utilisateur) | Capability | Owner |
|----------------------|------------|-------|
| Créer une facture | `invoice.create` | ComptaPilot |
| Envoyer une facture | `invoice.send` | ComptaPilot |
| Annuler une facture | `invoice.cancel` | ComptaPilot |
| Créer un devis | `proposal.create` | SalesPilot |
| Ajouter un client | `customer.create` | ComptaPilot |
| Créer un lead | `lead.create` | SalesPilot |
| Convertir un lead | `lead.convert` | SalesPilot |
| Créer une opportunité | `opportunity.create` | SalesPilot |
| Marquer opportunité gagnée | `opportunity.win` | SalesPilot |
| Importer un document | `document.import` | DocPilot |
| Classer un document | `document.classify` | DocPilot |
| Ouvrir un ticket | `ticket.create` | SupportPilot |

Une Intent peut aussi résoudre vers un **workflow** (plusieurs capabilities enchaînées) — Orchestrator orchestre, Pilots exécutent.

---

## Types d’Intent (conceptuels)

| Type | Exemple | Traitement |
|------|---------|------------|
| **Commande simple** | Créer une facture | 1 capability |
| **Commande workflow** | Clôturer prospect gagné | Plusieurs capabilities |
| **Navigation** | Ouvrir SalesPilot | Launcher / route (Orchestrator optionnel) |
| **Recherche** | Trouver facture X | Search Engine → deep-link |
| **Langage naturel** *(futur)* | Phrase libre | Couche interprétation → Intent structurée |

---

## Contenu conceptuel d’une Intent

| Élément | Rôle |
|---------|------|
| Formulation / libellé | Ce que l’utilisateur a choisi ou dit |
| Type | Commande / workflow / navigation / recherche / NL |
| Contexte org | Organisation active |
| Acteur | Utilisateur à l’origine |
| Paramètres métier | Références minimales (pas dump) |
| Corrélation | Lien audit / suivi de bout en bout |

Pas de schéma technique ici — principes seulement.

---

## Rôle de l’Orchestrator

| Fait | Ne fait pas |
|------|-------------|
| Recevoir l’Intent | Exposer l’Intent comme API publique Pilot |
| Sélectionner capability / workflow | Inventer une capability absente du registry |
| Vérifier routage et préconditions plateforme | Appliquer TVA / scoring / classification |
| Appeler le Pilot owner | Contourner un refus permission |
| Corréler Intent → Events → Graph | Posséder les données métier |

```
Intent ──► Orchestrator ──► Capability ──► Pilot
                │
                └──► Workflow (N capabilities) si besoin
```

---

## Préparation langage naturel (conceptuel)

```
Phrase libre
    │
    ▼
Couche d’interprétation (future)
    │  produit une Intent structurée
    ▼
Même pipeline Intent → Orchestrator → Capability
```

| Règle NL | Contenu |
|----------|---------|
| NL ne court-circuite pas | Toujours passer par Intent structurée |
| Ambiguïté | Demander clarification UX — ne pas deviner une capability destructive |
| Permissions | Identiques à une Intent manuelle |
| Audit | Corrélation Intent NL → capability → events |

---

## Anti-patterns

| Interdit | Pourquoi |
|----------|----------|
| Bouton UI qui appelle un autre Pilot en direct | Contourne Orchestrator |
| CC qui hardcode `invoice.create` sans Intent | Couplage UX ↔ métier |
| Intent = event (`invoice.created`) | Confusion fait / intention |
| Intent qui bypass permissions | Violation sécurité |
