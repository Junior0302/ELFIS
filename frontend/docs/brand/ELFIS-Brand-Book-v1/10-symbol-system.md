# 10 — Symbol System (Pilot Mark)

**Phase :** B0.2 — ELFIS Symbol System  
**Statut :** système de construction officiel  
**Portée :** documentaire — aucun SVG, PNG ou logo dessiné.

Ce document définit **comment** le Pilot Mark doit être construit.  
Il ne livre pas le dessin. Le tracé graphique relève de **B0.3**.

Horizon visé : **15 à 20 ans** de stabilité.

---

## 1 — Philosophie

### Pourquoi ce symbole existe

ELFIS Core relie des expertises métier distinctes. Le Pilot Mark existe pour rendre visible, en un seul signe, cette **connexion** — pas une discipline isolée.

Il n’existe **pas** pour représenter la comptabilité, ni les ventes, ni les documents.  
Il existe pour représenter **la plateforme qui unit les Pilot**.

### Ce qu’il raconte

| Narratif | Lecture |
|----------|---------|
| **Connexion** | Des parties distinctes forment un tout cohérent |
| **Pilotage** | Une direction claire, un cap commun |
| **Modularité** | Chaque Pilot est une unité ; la plateforme les assemble |
| **Continuité** | Le même signe traverse tous les produits |

### Émotion transmise

- Confiance calme (pas d’agressivité commerciale)
- Maîtrise (pas de complexité décorative)
- Ouverture (pas de symbole fermé « bunker »)
- Premium sobre (pas de gadget tendance)

### Valeurs portées

Précision · Cohérence · Continuité · Évolutivité · Clarté

### Interdit narratif

Le Mark ne doit jamais suggérer :

- uniquement la finance / la compta ;
- un outil unique ;
- une mode visuelle datée (néomorphisme, glassmorphism forcé, etc.) ;
- une mascotte ou un personnage.

---

## 2 — Point de départ : le symbole actuel

Le symbole actuellement en circulation est un **point de départ conceptuel**, pas un logo final à recolorer.

### Forces à conserver (intention)

| Force | Pourquoi la garder |
|-------|---------------------|
| Reconnaissance déjà amorcée | Continuité pour les utilisateurs existants |
| Lisibilité potentielle en petit format | Favicon / launcher |
| Identité « suite » plutôt qu’illustration métier | Alignée plateforme |
| Simplicité relative | Base pour 15–20 ans |

### Faiblesses à corriger (intention)

| Faiblesse | Risque | Direction d’évolution |
|-----------|--------|------------------------|
| Association historique à ComptaPilot | Confusion Master Brand | Neutraliser toute lecture « finance only » |
| Géométrie éventuellement trop spécifique / datée | Obsolescence | Simplifier, géométriser, grille stricte |
| Manque de règles de construction | Déclinaisons incohérentes | Symbol System (ce document) |
| Variantes non documentées | Usages sauvages | Guidelines B0.2 §9 / doc 11 |

### Règle

> **Ne pas simplement recolorer.**  
> Étudier → conserver l’intention → reconstruire sur grille → valider extensibilité.

Ce qui est conservé : **l’idée de connexion / pilotage**.  
Ce qui évolue : **géométrie, proportions, système, indépendance vs ComptaPilot**.

---

## 3 — Symbol System (grille de construction)

Tout tracé futur du Pilot Mark doit obéir à cette logique.  
Les valeurs sont exprimées en **unités de grille U** (relatives), pas en pixels absolus.

### 3.1 Grille

| Paramètre | Règle |
|-----------|--------|
| Grille de base | Carré **8 × 8 U** (zone de dessin du glyphe) |
| Module | **1 U** = plus petite unité de construction |
| Origine | Centre géométrique du carré 8×8 |
| Alignement | Tous les sommets majeurs sur intersections de grille |

### 3.2 Axes

- **Axe vertical** central (symétrie préférée, asymétrie légère autorisée si justifiée et documentée)
- **Axe horizontal** central
- Axes secondaires à 45° uniquement si la forme l’exige — pas de angles « libres »

### 3.3 Angles

| Autorisé | Interdit |
|----------|----------|
| 90°, 45°, 30°/60° (si grille le permet) | Angles arbitraires non snappés |
| Coins arrondis contrôlés (voir rayons) | Courbes Bézier décoratives sans module |

### 3.4 Épaisseurs

| Rôle | Épaisseur |
|------|-----------|
| Trait principal (stroke) | **1,0 U** |
| Trait secondaire (si besoin) | **0,5 U** |
| Interdiction | Traits < 0,5 U dans le Mark maître (illisibles en favicon) |

En solid fill (version plein), les masses doivent rester dérivables de la même grille stroke.

### 3.5 Espaces intérieurs

- Contreformes ≥ **1 U** (sinon bouchage en petite taille)
- Pas de « trous » décoratifs inférieurs à 1 U
- Densité visuelle : viser **équilibre plein / vide** (~40–60 % de surface active dans le carré)

### 3.6 Rayons

| Élément | Rayon |
|---------|--------|
| Coins externes | **0,5 U** à **1 U** max |
| Coins internes | ≤ coins externes |
| Interdiction | Rayons « blob » ou variables non documentés |

### 3.7 Alignements & répétition

- Éléments répétés (branches, nœuds, segments) : **même module**, même écart
- Logique de répétition = **connexion de nœuds** ou **segments orientés**, jamais collage d’icônes métier
- Nombre de « unités narratives » (nœuds / segments) : **3 à 5** — assez pour « réseau », pas assez pour « labyrinthe »

### 3.8 Zone optique

Le glyphe s’inscrit dans un **cercle optique** inscrit dans le 8×8 (marge visuelle), même si le bounding box est carré — pour éviter l’effet « trop bas » ou « trop à gauche » à côté d’un wordmark.

---

## 4 — Extensibilité (règle officielle)

### Règle d’or

> **Aucun nouveau Pilot ne redessine le Pilot Mark.**  
> Les Pilot futurs héritent du même glyphe + teinte / lockup.

Pilot prévus sans redessin de famille :

- SupportPilot  
- QualityPilot  
- AIPilot  
- ProcurementPilot  
- OperationsPilot  
- et tout Pilot ultérieur

### Ce qui change par Pilot

| Partagé (immuable) | Variable (par Pilot) |
|--------------------|----------------------|
| Géométrie du Pilot Mark | Couleur primary / accent (palette Brand Book) |
| Grille 8×8, strokes, rayons | Wordmark du produit |
| Zone de protection | Présence optionnelle de `by ELFIS Core` |
| Animations système | — |

### Ce qui est interdit pour étendre la famille

- Ajouter un pictogramme métier dans le Mark (casque RH, balance Legal, etc.)
- Modifier le nombre de nœuds / segments par produit
- Créer un « sous-mark » incompatible
- Versionner le Mark par année marketing

### Ajout d’un nouveau Pilot — procédure Brand

1. Attribuer une couleur primary (Brand Book §05).  
2. Créer le lockup : **Pilot Mark + wordmark**.  
3. Ne toucher **aucune** ancre géométrique du Mark.  
4. Valider contraste / petites tailles.  
5. Publier dans le kit B0.3+ — sans fork du glyphe.

---

## 5 — Couleurs — philosophies & choix officiel

Le Mark ELFIS Core **peut** intégrer des couleurs de l’écosystème, mais toujours de façon **élégante, sobre, premium**.

### Option A — Monochrome

| Avantages | Inconvénients |
|-----------|----------------|
| Intemporel, premium, imprimable | Moins « écosystème » au premier regard |
| Parfait favicon / watermark | Différenciation produit uniquement via wordmark / teinte shell |
| Zéro risque d’effet « arc-en-ciel cheap » | |

### Option B — Accent multicolore

| Avantages | Inconvénients |
|-----------|----------------|
| Raconte explicitement la diversité des Pilot | Risque jouet / startup datée |
| Fort en marketing | Fragile en petite taille, monochrome forcé, fax/print |
| | Maintenance (chaque Pilot = nouvelle couleur dans le glyphe) |

### Option C — Dégradé maîtrisé

| Avantages | Inconvénients |
|-----------|----------------|
| Sensation premium moderne | Dépend des supports (print, fax, broderie) |
| Une seule forme, richesse visuelle | Difficile à animer proprement ; risque mode |

### Direction officielle B0.2

> **Option A — Monochrome comme maître.**  
> Teinte unique = couleur de la marque porteuse (navy ELFIS Core, ou primary du Pilot dans un lockup produit).

**Complément autorisé (secondaire) :**

- Sur **grandes surfaces marketing uniquement**, une variante « constellation » peut utiliser jusqu’à **3 accents** de l’écosystème **hors du glyphe** (fond, halo, filet) — jamais plus de 2 couleurs **dans** le glyphe lui-même.
- Le glyphe maître reste **1 couleur + fond**.

**Interdit comme maître :** Option B full multicolore dans le Mark · Option C dégradé comme fichier source unique.

---

## 6 — Déclinaisons (catalogue système)

Chaque usage référence une **variante nommée**. Aucun fichier n’est produit en B0.2 ; les noms sont contractuels pour B0.3.

| Variante | Usage | Contrainte |
|----------|--------|------------|
| **Mark / Principal** | Logo glyphe référence | Grille 8×8, monochrome |
| **Mark / Réduit** | Espaces serrés | Même glyphe ; pas de simplification sauvage sauf version « Micro » validée |
| **Icône** | Launcher, nav | Carré 1:1, zone de protection |
| **Favicon** | Navigateur | Micro-lisibilité ; éventuellement version Micro |
| **App mobile** | Icon iOS/Android | Safe area store ; fond solid optionnel |
| **Avatar** | Profil org / produit | Cercle de recadrage |
| **Watermark** | Docs / PDF | Opacité basse, monochrome |
| **Loader** | Chargement | Version animable (traits/nœuds) |
| **Notification** | Badge app | Mark miniature + pastille système |
| **PDF / Print** | Documents | Noir ou navy 100 % ; pas de transparence critique |
| **Impression** | Goodies | 1–2 tons max |
| **Monochrome clair** | Fond sombre | Blanc / secondary claire |
| **Monochrome foncé** | Fond clair | Navy / primary / noir |
| **Petite taille** | ≤ 16–24 px | Version Micro si nécessaire |
| **Grande taille** | Hero / signalétique | Mark Principal ; détail autorisé |

### Version Micro (règle)

Si le Mark Principal perd des détails ≤ 16 px, une **Micro** est autorisée **une seule fois** : même silhouette, détails fusionnés, **même grille**. Pas de second concept.

---

## 7 — Animation (système motion)

Le mouvement doit exprimer **la connexion des applications**, pas un spectacle.

### Principes

- Durée courte (≈ 200–600 ms apparition ; loaders cycliques sobres)
- Easing : ease-out / standard Design System
- `prefers-reduced-motion` : état final statique immédiat
- Pas de morphing vers une icône métier
- Pas de bounce excessif / neon / particules

### Motifs autorisés

| Motif | Description | Usages |
|-------|-------------|--------|
| **Apparition** | Fade + léger scale 0,96 → 1 | Landing, login |
| **Connexion** | Segments / nœuds s’assemblent dans l’ordre | Loader, first paint |
| **Rotation contrainte** | Rotation ≤ 15° ou orbit d’un nœud secondaire | Idle launcher (optionnel) |
| **Loading** | Parcours d’un trait le long du path | Spinners marque |
| **Launcher** | Mark stable ; halo accent plateforme | App Launcher |
| **Transition produit** | Mark reste ; **couleur / wordmark** changent | Compta ↔ Sales |

### Interdit

- Rotation 360° continue du Mark entier comme identité
- Explosion / reconstruction chaotique
- Changement de géométrie entre produits pendant la transition

---

## 8 — Relation produits

### Héritage

```
Pilot Mark (glyphe unique)
    ├── Lockup ELFIS Core     (navy)
    ├── Lockup ComptaPilot    (vert)
    ├── Lockup SalesPilot     (bleu)
    ├── Lockup DocPilot       (orange)
    └── … futurs Pilot
```

### Partagé

- Géométrie, grille, protection, animations système, monochrome maître

### Ce qui change

- Couleur du Mark dans le lockup produit (= primary produit ou monochrome sur fond teinté)
- Wordmark
- Signature `by ELFIS Core` (Product Shell / marketing Pilot)

### Interdit

- Mark différent par Pilot
- Contour « aura » métier (feuilles Compta, éclairs Sales…)
- Remplacer le Mark par l’initiale seule comme symbole mère (l’initiale reste un **fallback UI**, pas le Pilot Mark)

---

## 9 — Synthèse pour le designer (B0.3)

Avant de tracer :

1. Grille 8×8 U, centre, axes  
2. 3–5 unités narratives (connexion)  
3. Stroke 1 U / contreformes ≥ 1 U  
4. Monochrome maître  
5. Test 16 px + 512 px + monochrome clair/foncé  
6. Aucune lecture « compta only »

---

## Documents liés

- [11 — Pilot Mark Guidelines](./11-pilot-mark-guidelines.md) — usage & interdictions  
- [12 — Brand Assets Roadmap](./12-brand-assets-roadmap.md) — préparation B0.3  
- [02 — Pilot Mark](./02-pilot-mark.md) — définition B0.1  
- [05 — Palette](./05-palette-officielle.md) · [06 — Design DNA](./06-design-dna.md)
