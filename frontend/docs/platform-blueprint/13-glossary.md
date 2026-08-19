# 13 — Glossaire

**ELFIS Platform Blueprint V1**

Termes officiels. En cas d’ambiguïté dans une discussion produit / tech, ce glossaire fait foi avec le document consolidé [14](./14-platform-blueprint-v1.md).

---

## A

**Aura**  
Couche d’intelligence / assistance transversale (couche 3). **N’est pas un Pilot.** Ne possède pas les données métier.

**Autonomie (Loi 1)**  
Capacité d’un Pilot à fonctionner sans les autres Pilots.

---

## B

**Banking**  
Domaine d’ownership des connexions et flux bancaires (cible architecture). Compta consomme ; n’absorbe pas.

**Blueprint**  
Document fondateur d’architecture plateforme (ce dossier). Référence officielle V1.

---

## C

**Capacité**  
Contrat d’exposition (API, intent, événement, projection) qu’un owner offre aux consommateurs — par opposition à un « module » couplé.

**ComptaPilot**  
Pilot owner de la facturation fiscale, de la comptabilité et de la finance associée.

**Core (ELFIS Core)**  
Couche 1 — socle plateforme : org, shell, Relations, vault, communications, contrats, Design System…

**Command Center**  
Palette globale Cmd/Ctrl+K (navigation + hits Search Engine V1). Owner exclusif du raccourci ⌘K.

---

## D

**Design System**  
Langage UI / tokens / composants officiels partagés par la plateforme et les Pilots.

**Domain separation**  
Chantier documenté de séparation des domaines et ownership (voir `frontend/docs/domain-separation/`).

---

## E

**Enrichissement (Loi 2)**  
Quand un autre Pilot est actif, le Pilot courant s’enrichit via capacités — sans absorber le domaine.

---

## I

**Insight Framework**  
Capacité Core de présentation d’alertes, analyses, suggestions, validations (contrat `Insight`). Indépendante des Pilots ; ne calcule pas et n’invente pas confiance / source. Distinct du Widget Framework (conteneurs vs contenu signal).

**Intent**  
Demande d’action routée (souvent via Orchestrator) vers le Pilot owner capable de l’exécuter.

**Inventory**  
Domaine d’ownership catalogue / prix / stock (cible). Expose des capacités ; n’est pas « un module dans Compta ».

---

## O

**Orchestrator**  
Infrastructure de coordination (intents, events). **Ne possède pas** les entités métier.

**Ownership**  
Règle « une donnée → un propriétaire unique » (Loi 3).

---

## P

**Pilot**  
Application métier autonome, activable, spécialisée, intégrable. Couche 2.

**Platform Shell**  
Chrome UI plateforme (topbar, launcher, search, notifs, profil) appartenant à Core.

**Product Shell**  
Cadre UI du Pilot actif (sidebar, accent, workspace).

---

## R

**Relations (Shared Relations)**  
Surface / contrat Core pour l’identité des parties (clients, fournisseurs…). Projection actuelle ; Party unifié = suite (S1.3+).

---

## S

**SalesPilot**  
Pilot owner du pipeline, des opportunités et devis commerciaux (avant facture définitive).

**Search Engine V1**  
Moteur fuzzy / index backend (FTS). Source technique unique — non dupliqué par Smart Search.

**Smart Search**  
Couche UX + contrats communs (`SearchResult`, scopes, combobox) au-dessus de Search Engine V1 et des APIs domaine. Capacité Core P1.0.

---

## U

**Universal Pickers**  
Framework de sélecteurs (Relation, Customer, Supplier, Document, Product) consommant Smart Search. Capacité Core P1.0.

---

## W

**Widget Framework**  
Coquille UI produit-agnostique pour widgets (loading, variants, footer source…). Pas un Pilot ; pas un owner de données.

---

## Z

**Zero ressaisie**  
Interdiction de faire retaper une information déjà connue de la plateforme (hors correction volontaire chez l’owner).

**Zero verrou**  
Garantie d’activer / désactiver un Pilot sans perte des données owned ; pas de prise en otage.

---

## Trois Lois (rappel)

1. Autonomie  
2. Enrichissement  
3. Un seul propriétaire
