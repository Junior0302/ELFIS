# UI Shell — documentation

Docs ciblées **chrome shell produit** (PlatformShell / ComptaPilot), hors Composer et hors redesign global.

## Index

| Doc | Contenu |
|-----|---------|
| [01 — Audit collapse](./01-sidebar-collapse-layout-audit.md) | Cause bande vide (état nav ≠ largeur grid) |
| [02 — Source unique](./02-sidebar-width-source-of-truth.md) | Variables `--product-sidebar-*`, layout cible |
| [03 — Implémentation](./03-sidebar-collapse-implementation.md) | Fichiers + comportements UI.P1 |
| [04 — Tests](./04-sidebar-collapse-test-plan.md) | SC01–SC40 + manuels SM01–SM20 |
| [05 — GO/NO-GO](./05-sidebar-collapse-go-nogo.md) | 11 critères puis STOP |
| [06 — 2ᵉ bouton menu](./06-redundant-menu-button.md) | Audit + suppression toggle topbar produit |
| [07 — Tests bouton menu](./07-redundant-menu-button-test-plan.md) | MB01–MB20 + manuels |
| [08 — GO/NO-GO bouton menu](./08-redundant-menu-button-go-nogo.md) | 9 critères puis STOP |

## Phase UI.P1

Correction du collapse sidebar ComptaPilot : une variable CSS partagée synchronise rail et contenu.

## Phase UI.P2

Suppression du 2ᵉ bouton menu topbar (toggle sidebar produit) ; un seul hamburger ELFIS ; nav produit mobile via contrôle distinct dans le contenu.
