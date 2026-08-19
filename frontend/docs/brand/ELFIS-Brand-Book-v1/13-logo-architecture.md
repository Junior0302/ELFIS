# 13 — Logo Architecture

**Phase :** B0.3 — Pilot Logo Architecture  
**Statut :** architecture officielle de la famille de logos  
**Portée :** documentaire — **aucun SVG, PNG ou logo final dessiné**.

Complète sans contredire :

- [B0.1](./README.md) — Brand Book Foundation  
- [B0.2](./10-symbol-system.md) — Symbol System  

---

## 1 — Audit de conformité (B0.1 / B0.2)

| Décision antérieure | Statut B0.3 |
|---------------------|-------------|
| ELFIS Core = plateforme ; Pilot = apps | Confirmée |
| Pilot Mark = symbole mère unique | Confirmée — base de toute la famille |
| Grille 8×8 U, stroke 1 U, monochrome maître | Confirmée — inchangée |
| Master Brand → Product Brands | Affinée ci-dessous en chaîne logo |
| `by ELFIS Core` | Intégré comme **Signature** de lockup |
| Nomenclature CamelCase / ELFIS Core | Confirmée — Wordmark System |
| Extensibilité sans redessin (AIPilot, etc.) | Confirmée |

B0.3 **n’introduit aucun second symbole** et **ne dessine pas** encore.

---

## 2 — Hiérarchie officielle

```
Pilot Mark          ← glyphe unique (Symbol System B0.2)
    ↓
Master Brand         ← ELFIS Core (plateforme)
    ↓
Product Brand        ← ComptaPilot, SalesPilot, DocPilot, …
    ↓
Product Lockup       ← composition Mark + wordmark (+ options)
```

### Qu’est-ce qui ne change **jamais** ?

| Élément | Immuable |
|---------|----------|
| **Pilot Mark** | Géométrie, grille, stroke, rayons, narratif « connexion » |
| **Une seule famille typo wordmark** | Même logique pour tous les noms |
| **Une seule philosophie visuelle** | Design DNA B0.1 / B0.2 |
| **Règles de protection / tailles** | Guidelines Mark |
| **Structure de lockup** | Ordre des éléments, variants nommées |

### Qu’est-ce qui **change** ?

| Niveau | Variable |
|--------|----------|
| **Master Brand** | Wordmark `ELFIS Core` · couleur navy · usages plateforme |
| **Product Brand** | Wordmark produit · primary produit · mission / émotion |
| **Product Lockup** | Combinaison Mark teinté + nom + signature optionnelle · format (H/V) |

---

## 3 — Structure d’un logo ELFIS

Tout logo de la famille se décompose ainsi :

| Élément | Définition | Obligatoire ? |
|---------|------------|---------------|
| **Pilot Mark** | Glyphe mère | **Oui** pour lockups symbole ; non pour « Nom seul » |
| **Wordmark** | Nom officiel en typo système | **Oui** dès qu’un nom est affiché |
| **Baseline** | Tagline courte (mission) | **Non** — layout / marketing, pas dans le fichier logo maître |
| **Signature** | `by ELFIS Core` | **Non** — obligatoire en Product Shell / marketing Pilot ; absente sur surfaces 100 % Master Brand |
| **Couleur** | Teinte du Mark / du wordmark selon marque | **Oui** (monochrome maître + règle de fond) |
| **Zone de protection** | Espace libre autour du lockup | **Oui** dès publication |

### Assemblages types

```
[Mark]                    → symbole seul
[Mark][Wordmark]          → lockup standard
[Mark][Wordmark]
      by ELFIS Core       → lockup produit signé
[Wordmark]                → nom seul (contraint)
```

La **baseline** (ex. « Une plateforme. Plusieurs expertises. ») vit dans les compositions de page, **pas** dans le fichier logo source.

---

## 4 — Wordmark System

### Règles communes

| Règle | Valeur |
|-------|--------|
| Capitalisation | Exacte Brand Book (`ELFIS Core`, `ComptaPilot`, …) |
| Famille typo | **Une seule** famille wordmark pour toute la suite (à figer au tracé) |
| Graisse | Une graisse primaire (ex. SemiBold/Bold) + une secondaire optionnelle pour `by` |
| Tracking | Identique pour tous les `*Pilot` ; `ELFIS Core` suit la même famille avec espace mot |
| Alignement optique | Baseline du wordmark alignée sur l’axe optique du Mark |
| Espacement Mark → Wordmark | **0,5 H** à **0,75 H** (H = hauteur Mark) |

### Liste officielle des wordmarks

`ELFIS Core` · `ComptaPilot` · `SalesPilot` · `DocPilot` · `HRPilot` · `LegalPilot` · `MarketingPilot` · `InventoryPilot` · `ProjectPilot` · `SupportPilot` · `AIPilot` · (+ futurs `XxxPilot`)

### Exceptions autorisées

| Exception | Condition |
|-----------|-----------|
| Abréviation UI (`ELFIS`) | Uniquement espaces extrêmes (≤ 16 px) — pas un logo officiel |
| Casse forcée CSS | Interdite sur wordmark Brand |
| Traduction | Interdite |
| `by` en italique | Autorisé **uniquement** pour la Signature, graisse plus légère |

### Interdit

- Deux familles typo (display landing ≠ wordmark logo sans validation Brand majeure)  
- Contour / ombre sur le wordmark  
- Wordmark dans le glyphe Mark  

---

## 5 — Lockups officiels

Chaque variante a un **nom de système** (contrat pour futurs fichiers).

| ID | Composition | Usages types |
|----|-------------|--------------|
| `mark-only` | Mark | Favicon, notification, loader |
| `mark-name-h` | Mark + nom · horizontal | Topbar, headers, landing |
| `mark-name-v` | Mark au-dessus du nom · vertical | Splash, mobile, stacked |
| `name-only` | Nom seul | Mentions textuelles, contraintes extrêmes |
| `product-signed-h` | Mark + nom + `by ELFIS Core` · H | Sidebar produit, marketing Pilot |
| `product-signed-v` | Idem · V | Splash produit |
| `launcher` | Mark (évent. pastille) | App Launcher |
| `sidebar` | Mark + nom (signed recommandé) | Product Shell |
| `splash` | `mark-name-v` ou signed-v | Splash / onboarding |
| `watermark` | Mark ou name-only · opacité basse | PDF, docs |
| `pdf` | Monochrome print | Documents |
| `favicon` | Mark Micro | Navigateur |

Règles :

- **Master Brand** n’utilise **pas** `product-signed-*`.  
- **Product Brand** privilégie `product-signed-*` hors shell déjà contextualisé.  
- `name-only` n’est jamais le fichier maître d’un Pilot.

---

## 6 — Héritage

### Ce que **tous** les Pilot héritent d’ELFIS

- Pilot Mark (géométrie)  
- Wordmark System  
- Design DNA / motion system  
- Composants & shells plateforme  
- Nomenclature · checklist cohérence  
- Signature `by ELFIS Core` (règle d’emploi)

### Spécifique par marque

| Marque | Hérite | Lui est propre |
|--------|--------|----------------|
| **ELFIS Core** | Mark, DNA, typo | Wordmark `ELFIS Core` · navy · surfaces publiques · Platform Shell |
| **ComptaPilot** | Mark, DNA, typo, signature | Wordmark · vert · émotion finance · Product Shell finance |
| **SalesPilot** | idem | Wordmark · bleu · émotion croissance · shell CRM |
| **DocPilot** | idem | Wordmark · orange · émotion organisation · shell docs |
| **Autres / AIPilot** | idem | Wordmark · primary Brand Book · fiche produit |

Rien d’autre n’est « propre » au niveau **logo** : pas de second symbole, pas de grille concurrente.

---

## 7 — Contraintes dures (interdictions)

| Interdiction | Raison |
|--------------|--------|
| Jamais deux symboles différents | Une famille = un Mark |
| Jamais deux grilles | 8×8 U unique |
| Jamais deux styles d’angles | DNA Symbol System |
| Jamais deux familles typographiques wordmark | Un système |
| Jamais deux philosophies visuelles | Un ADN |
| Jamais recoloration « arc-en-ciel » du glyphe maître | Option A B0.2 |
| Jamais pictogramme métier greffé sur le Mark | Extensibilité |

---

## 8 — Préparation des directions créatives (entrée B0.4)

B0.4 explorera **3 directions créatives** pour chaque marque prioritaire, **sans** sortir du cadre suivant.

### Contraintes communes aux 12 explorations (3×4)

1. Même Pilot Mark (même géométrie)  
2. Monochrome maître + teinte de marque  
3. Wordmark System  
4. Au moins les lockups `mark-only`, `mark-name-h`, `product-signed-h` (Pilot)  
5. Tests 16 px / fond clair / fond sombre  
6. Aucune lecture « compta only » pour le Mark partagé  

### Briefs par marque

| Marque | Les 3 directions doivent explorer… | Garde-fous |
|--------|--------------------------------------|------------|
| **ELFIS Core** | Autorité plateforme · sobriété · « connexion » lisible | Navy ; pas de vert dominant |
| **ComptaPilot** | Confiance / précision / sérieux finance | Vert ; Mark inchangé ; ± signature |
| **SalesPilot** | Momentum / relation / clarté pipeline | Bleu ; Mark inchangé |
| **DocPilot** | Ordre / flux / connaissance | Orange Brand Book ; Mark inchangé |

Les directions varient **composition, graisse wordmark (dans la famille), rythme Mark–nom, traitement de fond** — **pas** le glyphe.

---

## Documents liés

- [14 — Product Brand Guidelines](./14-product-brand-guidelines.md)  
- [15 — Brand Consistency Checklist](./15-brand-consistency-checklist.md)  
- [10 — Symbol System](./10-symbol-system.md) · [11 — Guidelines](./11-pilot-mark-guidelines.md)
