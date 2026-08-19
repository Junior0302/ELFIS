# 15 — Full Focus Test Plan

## Automatisés FF01–FF40

Fichier : `src/pages/facturation/facturation-full-focus.test.tsx`

Couvre path detection, flags layout, header, workspace, exit confirm, confirmation panel, a11y landmarks, deep links, export framework.

Régression UXF01–40 : `facturation-ux-review.test.tsx` (toujours verts).

## Manuel MF01–MF25 — À tester manuellement

| ID | Scénario | Statut |
|----|----------|--------|
| MF01 | Pop-in type → Composer sans sidebar Compta | À tester manuellement |
| MF02 | Pas de nav Facturation horizontale | À tester manuellement |
| MF03 | Pas de Guide Banner | À tester manuellement |
| MF04 | Topbar : hamburger + Apps + org + profil | À tester manuellement |
| MF05 | Éditeur ~⅔ / preview ~⅓ desktop | À tester manuellement |
| MF06 | Scroll indépendant panneaux | À tester manuellement |
| MF07 | Sections blanches (pas fond vert) | À tester manuellement |
| MF08 | Autosave reste en Focus | À tester manuellement |
| MF09 | Select client reste en Focus | À tester manuellement |
| MF10 | Product picker overlay dans Focus | À tester manuellement |
| MF11 | Refresh URL conserve Focus + type | À tester manuellement |
| MF12 | Deep link favori `?type=facture` | À tester manuellement |
| MF13 | Annuler dirty → confirm | À tester manuellement |
| MF14 | Annuler vide → Documents | À tester manuellement |
| MF15 | ← Documents dirty → confirm | À tester manuellement |
| MF16 | 1er save → confirmation Focus | À tester manuellement |
| MF17 | Ouvrir le document depuis confirm | À tester manuellement |
| MF18 | Revenir Documents depuis confirm | À tester manuellement |
| MF19 | Créer un autre → pop-in | À tester manuellement |
| MF20 | Envoi → confirmation dans Focus | À tester manuellement |
| MF21 | Laptop preview collapse | À tester manuellement |
| MF22 | Mobile 1 col + toggle aperçu | À tester manuellement |
| MF23 | Escape ferme overlay, pas Composer | À tester manuellement |
| MF24 | Zoom / fullscreen PDF inchangés | À tester manuellement |
| MF25 | Pas de flash shell classique | À tester manuellement |

## Tableau F1.3.1 (complément)

Les MR19–MR30 de `09-test-plan.md` restent valides ; MF01–MF25 couvrent le **Full Focus** (shell produit masqué).
