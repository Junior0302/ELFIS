# 53 — Immediate line deletion diagnostic

> **Note numérotation :** le brief utilisateur citait F1.3.2.2 / docs 47–52 ; ces slots étaient déjà pris par *catalog overlay layering*. Cette correction utilise **53–58**.

## Reproduction

1. Nouvelle facture → client → étape Produits  
2. Ajouter via catalogue (« Parcourir le catalogue » → Ajouter)  
3. Supprimer la ligne dans l’éditeur  
4. **Observé :** la désignation reste visible dans la zone Produits (slot `ps-picker__selected`) ; perception « ligne toujours là »  
5. Continuer → Retour (remount `LinesSection`) → disparition

## Collections

| Surface | Source réelle | Divergence ? |
|---------|---------------|--------------|
| `LineEditor` | `draft.products` | Non — se met à jour |
| Aperçu / totaux / controls / insights | `draft` + dérivés | Non si draft OK |
| **ProductPicker `selected`** | **`lastPicked` (useState local)** | **Oui** — indépendant de `draft.products` |
| Autosave payload | `buildPayload()` ← `draft` closuré | Race possible si snapshot stale |

## Cause exacte

1. **État local divergent `lastPicked`**  
   Après `addFromSearchResult`, `setLastPicked(item)` alimente `ProductPicker selected={lastPicked}` → bloc `.ps-picker__selected` (titre + sous-titre).  
   `removeLine` met à jour `draft.products` mais **ne clear pas** `lastPicked`.  
   Remount (`guidedStep !== 'items'` puis retour) réinitialise `useState(null)` → « corrige » l’UI.

2. **Ajouts catalogue via closure stale**  
   `onChange([...draft.products, next])` lit `draft.products` au moment du render — multi-ajouts rapides / delete+add peuvent diverger. Il faut **updater fonctionnel** `setDraft(d => …)`.

3. **Autosave**  
   `saveDraft` / `buildPayload` ferment sur `draft` ; une requête en vol ne réinjecte pas les lignes (patch id seulement) — OK — mais un epoch/ref évite toute ambiguïté last-write-wins.

## Pourquoi remount « corrige »

`LinesSection` est monté conditionnellement (`guidedStep === 'items'`). Continuer/Retour démonte/remonte → `lastPicked = null` → plus de fantôme picker. `draft.products` était déjà correct.

## Hors scope

Workflow modal, catalogue modal layering, calculs métier, PDF engine, Vault, Billing, F1.4.
