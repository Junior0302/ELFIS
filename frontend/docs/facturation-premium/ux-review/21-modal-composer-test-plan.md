# 21 — Modal Composer Test Plan

## Automatisés MC01–MC40

Fichier : `src/pages/facturation/facturation-modal-composer.test.tsx`

Couvre routing modal, Documents monté, type→composer, dialog phases, dirty confirm 3 actions, a11y, inert, regress shell.

Régression : `facturation-ux-review.test.tsx`, `facturation-full-focus.test.tsx` (layout Focus réutilisé en page/tests), `facturation-spaces.test.tsx`.

## Manuel MD01–MD25 — À tester manuellement

| ID | Scénario | Statut |
|----|----------|--------|
| MD01 | Créer → pop-in type (petite) | À tester manuellement |
| MD02 | Type → agrandissement Composer sans flash Documents | À tester manuellement |
| MD03 | Documents visible flouté derrière | À tester manuellement |
| MD04 | Scroll Documents bloqué pendant modal | À tester manuellement |
| MD05 | Filtres / recherche conservés à la fermeture | À tester manuellement |
| MD06 | Desktop ~94vw × 92vh centré | À tester manuellement |
| MD07 | Laptop 96vw / 94vh | À tester manuellement |
| MD08 | Mobile plein écran | À tester manuellement |
| MD09 | Editor / preview ratio ~65/35 | À tester manuellement |
| MD10 | Scroll interne uniquement | À tester manuellement |
| MD11 | Escape ferme picker avant Composer | À tester manuellement |
| MD12 | Escape sur Composer vide → close | À tester manuellement |
| MD13 | Dirty → 3 boutons confirm | À tester manuellement |
| MD14 | Enregistrer et fermer | À tester manuellement |
| MD15 | Autosaved → close sans confirm | À tester manuellement |
| MD16 | Post-création reste dans dialog | À tester manuellement |
| MD17 | Revenir Documents refresh liste | À tester manuellement |
| MD18 | Créer un autre → pop-in type | À tester manuellement |
| MD19 | Deep link `/documents/new?type=facture` | À tester manuellement |
| MD20 | Refresh URL conserve modal + type | À tester manuellement |
| MD21 | Back navigateur ferme modal → Documents | À tester manuellement |
| MD22 | Legacy `/nouveau?type=` redirige modal | À tester manuellement |
| MD23 | Focus retour sur Créer un document | À tester manuellement |
| MD24 | CustomerPicker pas auto-ouvert | À tester manuellement |
| MD25 | Petite pop-in ≠ grand ComposerDialog (style) | À tester manuellement |
