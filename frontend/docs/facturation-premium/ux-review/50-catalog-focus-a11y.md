# 50 — Focus & a11y catalog submodal (F1.3.2.2)

## Focus trap

`useOverlayBehaviour` : trap Tab **uniquement** si `isTopOverlay`. Quand CatalogModal est ouvert, trap Composer suspendu automatiquement.

## Fermeture

Escape / X / Fermer / backdrop → ferme surface haute seulement. Si `ProductCreationDialog` ouvert → Escape ferme d’abord la création (`closeOnEscape` catalogue désactivé).

## Restore focus

`returnFocusRef` → bouton « Parcourir le catalogue ».

## A11y

`role="dialog"` · `aria-modal="true"` · `aria-labelledby` / `aria-describedby` · focus initial search.
