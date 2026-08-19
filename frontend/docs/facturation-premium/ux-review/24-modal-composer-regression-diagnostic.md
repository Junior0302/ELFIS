# 24 — Diagnostic régression Composer modal (F1.3.1.3)

## Symptôme observé

Après choix du type → courte animation → retour visuel Documents → **grand Composer modal n’apparaît pas** (ou flash puis disparition).

## Cause exacte

| Champ | Valeur |
|-------|--------|
| **Événement** | `navigate('/facturation/documents/new?type=…')` dans `DocumentCreateFlow.createFromType` |
| **Mécanisme** | `OverlayRouteBridge` détecte `pathname`+`search` change → `requestClose(id, 'route_change')` |
| **Fichier** | `frontend/src/design-system/overlays/OverlayRouteBridge.tsx` (l.14–25) |
| **Défaut** | `defaultCloseOnRouteChange('dialog') === true` (`overlayPriority.ts`) |
| **Force** | `route_change` ∈ `FORCE_CLOSE_REASONS` → ignore `dismissible=false` |
| **Handler** | `DocumentCreateFlow.onDialogRequestClose` → phase `composer` → `closeAll()` → `navigate('/facturation/documents')` |
| **Ligne logique** | `ComposerDialog` enregistre l’overlay **sans** `closeOnRouteChange: false` |

### Chaîne avant correctif

1. STATE 1 type ouvert (`ComposerDialog` / dialog Overlay Manager).
2. « Créer le document » → `setBridgeComposer(true)` + `onTypeOpenChange(false)` + `navigate(…/new?type=)`.
3. URL change → `OverlayRouteBridge` ferme le dialog (`route_change`).
4. `closeAll()` ramène `/facturation/documents` → overlay disparu, Documents seul.
5. Utilisateur voit un flash / retour Documents ; Composer jamais persisté.

### Causes secondaires (aggravantes, pas root)

| Élément | Effet |
|---------|--------|
| `createFromType` appelle `onTypeOpenChange(false)` | Booléen concurrent ; overlay dépendait du bridge URL |
| Booléens `typeOpen` + `bridgeComposer` + `composerMatch` | Pas une seule source de vérité |
| `FacturationComposerPage` `Navigate` si `!typeParam` | Redirect possible si type URL perdu |
| Tests MC sans `OverlayRouteBridge` | Régression non détectée |

**Ce n’est pas** un setTimeout manquant, ni un problème de dimensions CSS, ni un démontage Documents (nested route OK).

## Correction (F1.3.1.3)

1. **Une** state machine `ComposerModalStage` ; root persistant `DocumentCreationModalRoot`.
2. `closeOnRouteChange: false` sur le root création (URL sync ≠ fermeture).
3. Ignorer `route_change` dans le handler de fermeture du flux.
4. Transition type→composer = `stage = "composer"` seulement (pas close / pas restore focus page).
5. Supprimer redirects auto Composer vide / sans client / sans lignes.
6. Tests MM avec `OverlayRouteBridge` (preuve anti-régression).

## Preuve avant / après

| | Avant | Après |
|--|-------|-------|
| Overlay après Créer | Fermé par `route_change` | Reste ouvert, phase `composer` |
| URL `/documents/new?type=` | Déclenche close puis bounce Documents | Sync URL, modal persiste |
| Documents | Visible seul (régression) | Monté derrière, inert |
| Fermeture volontaire | N/A (déjà fermé) | Escape/Annuler → Documents immédiat |
