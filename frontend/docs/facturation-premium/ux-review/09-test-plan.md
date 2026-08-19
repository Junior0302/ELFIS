# 09 — Test plan

## Automatisés UXF01–UXF40

Fichier : `src/pages/facturation/facturation-ux-review.test.tsx`

Couvre nav, Documents CTA, pop-in a11y, ouverture Composer, freeform, pickers fermés, ligne libre, purge copy, focus, exit confirm, deep links.

## Manuel MR01–MR30 — À tester manuellement

| ID | Scénario | Statut |
|----|----------|--------|
| MR01 | Sidebar produit : 4 items Facturation | À tester manuellement |
| MR02 | Nav horizontale sans Nouveau | À tester manuellement |
| MR03 | Documents → Créer un document → pop-in | À tester manuellement |
| MR04 | Overlay blur + centrage | À tester manuellement |
| MR05 | Tab / Shift+Tab trap dans pop-in | À tester manuellement |
| MR06 | Flèches radiogroup types | À tester manuellement |
| MR07 | Escape ferme si rien engagé | À tester manuellement |
| MR08 | Backdrop ne ferme pas si type sélectionné | À tester manuellement |
| MR09 | Focus retourne sur le bouton CTA | À tester manuellement |
| MR10 | Créer → Composer type initialisé | À tester manuellement |
| MR11 | Pas de re-choix type dans Composer | À tester manuellement |
| MR12 | Deep link `?type=facture` favori | À tester manuellement |
| MR13 | CustomerPicker fermé au mount | À tester manuellement |
| MR14 | ProductPicker fermé au mount | À tester manuellement |
| MR15 | Ligne libre éditable sans picker | À tester manuellement |
| MR16 | Nouveau produit même picker ouvert | À tester manuellement |
| MR17 | Création client conserve brouillon | À tester manuellement |
| MR18 | Validations non triplées | À tester manuellement |
| MR19 | Focus mode largeur + nav cachée | À tester manuellement |
| MR20 | Preview sticky hauteur desktop | À tester manuellement |
| MR21 | Zoom / fullscreen PDF | À tester manuellement |
| MR22 | Laptop collapse preview | À tester manuellement |
| MR23 | Mobile pop-in full/bottom | À tester manuellement |
| MR24 | Mobile Composer 1 col | À tester manuellement |
| MR25 | Annuler confirm si dirty | À tester manuellement |
| MR26 | Annuler sans confirm si vide | À tester manuellement |
| MR27 | Autosave après premier save | À tester manuellement |
| MR28 | Command Center → facture typed | À tester manuellement |
| MR29 | Design : navy / accent / ombres légères | À tester manuellement |
| MR30 | Retour Documents post-création | À tester manuellement |

## Complément F1.3.1.1 Full Focus

Voir [15-full-focus-test-plan.md](./15-full-focus-test-plan.md) — FF01–FF40 automatisés + **MF01–MF25 À tester manuellement** (sidebar Compta, Guide, viewport, confirmation Focus).
