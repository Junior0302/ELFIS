# F1.3.1 — Audit runtime Pass 1

Audit des composants réels (code + comportement dérivé). **Aucune correction sur hypothèse** : chaque entrée cite fichier, état, événement, cause exacte.

Légende état : `OPEN` = irritant confirmé à corriger · `OK` = conforme · `KEEP` = conserver (route / compat).

---

## NAV Facturation

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| N1 | « Nouveau document » dans sidebar produit | `src/navModel.ts` | `navCategories` → `ventes.children` | OPEN | Render sidebar | Leaf `facturation-nouveau` → `/facturation/nouveau` | Retirer le leaf ; nav finale : Vue d’ensemble \| Documents \| Catalogue \| Activité |
| N2 | « Nouveau document » nav horizontale | `src/comptapilot/facturation/FacturationLayout.tsx` | `SPACES` | OPEN | Render `fp-spaces__nav` | Entrée `{ to: '/facturation/nouveau', label: 'Nouveau document' }` | Retirer de `SPACES` ; garder focus mode sur `/nouveau` |
| N3 | Exact-match path orphelin | `src/navModel.ts` | `NAV_EXACT_MATCH_PATHS` | OPEN | Match leaf | `/facturation/nouveau` encore listé alors que leaf retiré | Retirer l’entrée si leaf disparu (route Composer inchangée) |
| N4 | Carte Overview « Nouveau document » | `src/pages/facturation/FacturationOverviewPage.tsx` | `LINKS` | OPEN | Clic carte | Lien direct Composer | Remplacer par entrée Documents / CTA création via Documents |
| N5 | Command Center « Nouvelle facture » | `src/platform-command/commandModel.ts` | `QUICK_ACTION_CATALOG` / `COMMAND_CATALOG` | KEEP→ajust | Exécution commande | `href: '/facturation/nouveau'` sans type | Deep link `/facturation/nouveau?type=facture` (route conservée) |
| N6 | Financial Command Center | `src/comptapilot/financial-command-center/FinancialCommandCenter.tsx` | raccourci | KEEP→ajust | Clic | Même href sans type | Idem `?type=facture` |

---

## Documents = entrée

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| D1 | CTA primaire = Link Composer | `src/pages/FacturationPage.tsx` | `fp-header__actions` | OPEN | Clic « Nouveau document » | `<Link to="/facturation/nouveau">` | Bouton « Créer un document » → ouvre pop-in |
| D2 | Secondaire « Liste des devis » | même | `Link` `/devis` | OPEN | Clic | Doublon avec filtre `typeFilter === 'devis'` | Retirer le lien ; filtre/onglets restent |
| D3 | Page Documents = wrapper | `src/pages/facturation/FacturationDocumentsPage.tsx` | `FacturationDocumentsPage` | OK | — | Réutilise `FacturationPage` | Brancher pop-in dans `FacturationPage` |
| D4 | Formulaire « Créer » inline | `src/pages/FacturationPage.tsx` | section `Créer` | OPEN | Concurrence CTA | Deux chemins de création (form + Composer) | Masquer form création si `!editingId` ; garder édition |

---

## Pop-in Nouveau document

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| P1 | Aucune dialog de type | — | — | OPEN | — | Type choisi dans Composer step `document-choice` | Nouveau composant Dialog DS (`role=dialog`, modal, trap déjà dans `Dialog.tsx`) |
| P2 | Dialog DS prêt | `src/design-system/overlays/Dialog.tsx` | `Dialog` | OK | — | `aria-modal`, labelledby, Escape, backdrop, focus | Réutiliser `size="sm"` ; `closeOnBackdrop` seulement si rien engagé |
| P3 | Backdrop blur | `overlays.css` | `.ds-overlay-backdrop` | OK | — | `backdrop-filter: blur(2px)` déjà | Pas de nouveau framework overlay |

---

## Route Composer

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| C1 | Route `/facturation/nouveau` | `src/App.tsx` | lazy `FacturationComposerPage` | KEEP | Deep link / back | Route montée | Ne pas supprimer |
| C2 | Choix type dans Composer | `FacturationComposerPage.tsx` | `DocTypeStep` + step `document-choice` | OPEN | Mount sans type | Premier step wizard = re-choix type | Init `docType` via `?type=` ; sans type → redirect `documents?create=1` |
| C3 | Titre générique | même | `definition.title` | OPEN | Render header | `Nouveau ${docType}` ou « Nouveau document » | « Nouvelle facture » / « Nouveau devis » / « Nouvel avoir » |
| C4 | Prefill client | même | `customer_id` query | OK | Mount | Prefill API existant | Conserver |

---

## Wizard / Progression

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| W1 | Sidebar 10 étapes | `ComposerContainer.tsx` + Composer page | `ComposerSidebar` via `showSidebar` défaut true | OPEN | Render layout | `FACTURATION_WORKFLOW_STEPS` (10) passés à `definition.steps` | `showSidebar={false}` ; freeform sections |
| W2 | Progress = steps wizard | `ComposerProgress` | dots 10 | OPEN | Header | `steps={visibleSteps}` wizard | Remplacer par jalons données réelles (type, client, ≥1 ligne, requis, contrôles) |
| W3 | Footer Continuer/Retour | Composer page | `ComposerNavigation` + `useWizardNavigation` | OPEN | Clic | Navigation step-by-step | Retirer nav wizard UI (états métier workflow inchangés côté types) |
| W4 | Copy « Étape préparée » | `workflow/types.ts` + ShellSteps | steps send/archive/accounting | OPEN | Affichage | Descriptions littérales | Ne plus afficher ces steps en UI freeform |

---

## CustomerPicker

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| CP1 | Liste ouverte au mount | `UniversalPicker.tsx` | défaut `alwaysOpen = true` | OPEN | Mount | Panel toujours visible | Défaut `alwaysOpen = false` |
| CP2 | Recherche vide au mount | `RelationPicker.tsx` | `allowEmptyQuery: true`, `minChars: 0` | OPEN | Mount + alwaysOpen | `useSmartSearch` charge immédiatement | `allowEmptyQuery: false`, `minChars: 1` (Composer) |
| CP3 | Focus ouvre liste | `SmartSearch.tsx` | `onFocus={() => setOpen(true)}` | OPEN | Focus tab/clic | Ouvre même sans query ; avec empty query → liste | Garder ouverture au focus **sans** empty-query dump ; panel statut « tapez pour rechercher » |
| CP4 | Copy technique client | Composer `ClientStep` | description + meta Source/IDs | OPEN | Render | « CustomerPicker (Smart Search) », Relation ID, Customer ID | Terminologie métier ; masquer IDs debug |
| CP5 | Label création | `CustomerPicker.tsx` | `createAction.label` | OPEN | — | « Créer un client » | « + Ajouter un client » |
| CP6 | Création conserve sélection | `CustomerPicker` `createClient` | onSelect après create | OK | Submit | Reselect via `onSelect` | Conserver |

---

## ProductPicker / lignes

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| PP1 | Liste ouverte au mount | `ProductPicker` → UniversalPicker | alwaysOpen défaut true | OPEN | Mount | Idem CP1 | Closed-by-default |
| PP2 | Empty query liste | ProductPicker `allowEmptyQuery: true` | searchOptions | OPEN | Mount | Charge catalogue entier | minChars ≥ 1, allowEmptyQuery false |
| PP3 | Banner InventoryPilot / Source | `ProductPicker.tsx` L41–48 | UI status | OPEN | Render | Textes techniques | Retirer de l’UI |
| PP4 | Copy Smart Library | Composer `ProductsStep` | description | OPEN | Render | « Smart Library… InventoryPilot… » | Copy métier |
| PP5 | Pas de « ligne libre » dédiée | `ProductsStep` / `LineEditor` | — | OPEN | — | « Ajouter dessous » nécessite déjà une ligne ; empty state pousse catalogue | Bouton « Ajouter une ligne libre » sans ouvrir picker |
| PP6 | Création produit locale | `createProduct` + `api.createCatalogItem` | footer create | OK | Submit | Blueprint local | Conserver ; label « Nouveau produit » |

---

## Validations / Insights

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| V1 | Triplication contrôles | Composer page | Header status + `ComposerValidation` inspector + step controls/validation + `LiveInsightsPanel` (map issues) | OPEN | Derive | `controls` affichés 3+ fois ; insights re-mappent issues | Header = résumé ; section = inline ; panneau = insights à valeur ajoutée seulement (sans rejouer issues) |
| V2 | Insights confirmation redondants | `insights.ts` | `live:client-selected`, `live:product-added` | OPEN | Chaque sélection | Confirmations + validation | Garder attentions utiles ; éviter spam confirmation |

---

## Focus / Header / PDF / Exit

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| F1 | Focus masque nav espaces | `FacturationLayout` | `hidden={focusMode}` | OK | Path `/nouveau` | Nav secondaire hidden | Conserver |
| F2 | Double sortie Dashboard/Documents | Composer page | `exitToolbar` + `secondaryActions` Annuler | OPEN | Toolbar | Liens Dashboard + Documents dans contenu | Topbar minimale ; une sortie Documents / Annuler |
| F3 | Preview ratio | `composer-framework.css` | `--preview` ~30% | OPEN | Desktop | `minmax(12rem, 30%)` | Viser édition 60–68% / preview 32–40% |
| F4 | Annuler sans confirm | Composer `secondaryActions` cancel | si pas `createdDocId` | OPEN | Clic Annuler | `focus.exitTo('documents')` silencieux | Confirm si draft local non sauvé |
| F5 | Autosave | Composer `useEffect` debounce | après `createdDocId` | OK | Patch draft | Update API existante | Conserver |
| F6 | PDF sticky / zoom / fullscreen | `ComposerPreview` + page | états empty/loading/ready | OK | — | Moteur existant | Polish hauteur/empty uniquement |

---

## Responsive

| ID | Problème | Fichier | Composant | État | Événement | Cause exacte | Correction minimale |
|----|----------|---------|-----------|------|-----------|--------------|---------------------|
| R1 | Preview sous tablette | `composer-framework.css` media | layout | OK partiel | — | Preview under déjà | Vérifier laptop collapse via `previewCollapsed` |
| R2 | Pickers full mobile | platform-search CSS | — | OPEN | Mobile | Pas de full-sheet dédié | CSS mobile picker full-width si besoin ; jamais liste auto-ouverte |

---

## Tests existants impactés

| ID | Impact |
|----|--------|
| T1 | `navModel.test.ts` attend leaf `facturation-nouveau` |
| T2 | `facturation-spaces.test.tsx` attend lien Nouveau document |
| T3 | `FacturationPage.premium.test.tsx` attend « Liste des devis » |
| T4 | `platform-search.integration.test.tsx` attend liste ouverte au mount |

---

## Synthèse priorités Pass 1

1. Nav + Documents CTA + pop-in (N*, D*, P*)
2. Composer freeform + type query + sidebar off (C*, W*)
3. Pickers closed-by-default + ligne libre (CP*, PP*)
4. Dedup validation + purge copy (V*)
5. Focus/header/PDF/CSS + exit confirm (F*, R*)
6. Tests UXF + docs GO/NO GO
