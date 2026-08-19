# 58 — Rapport d’implémentation + GO/NO GO — Line deletion UI

> Brief utilisateur : F1.3.2.2 / docs 47–52 — **slots déjà pris** par catalog overlay layering. Cette correction = docs **53–58**.

## Verdict : **GO**

## Preuves

| Preuve | Résultat |
|--------|----------|
| LDI01–LDI40 | **40/40** passés (`facturation-line-deletion.test.tsx`) |
| Build | **OK** (`tsc -b && vite build`) |
| Docs | 53–58 présentes (catalog 47–52 non écrasées) |

## Critères GO (12)

| # | Critère | Statut |
|---|---------|--------|
| 1 | Diagnostic 53 cause exacte | GO |
| 2 | Source unique `draft.products` | GO |
| 3 | Remove immutable + nouvelle ref | GO |
| 4 | `lineKey` stable (pas index seul) | GO |
| 5 | Update optimiste immédiat | GO |
| 6 | Plus de `lastPicked` / selected fantôme | GO |
| 7 | Append / replace fonctionnels | GO |
| 8 | Preview / totaux / empty immédiats | GO |
| 9 | Autosave race guard | GO |
| 10 | Fade optionnel + reduced-motion | GO |
| 11 | Tests LDI + SI manuel | GO (LDI auto ; SI01–SI20 « À tester manuellement ») |
| 12 | Docs 53–58 + build | GO |

## Cause → fix (résumé)

| Cause | Fix |
|-------|-----|
| `lastPicked` / `ProductPicker selected` fantôme | Suppression de `lastPicked` ; plus de slot `.ps-picker__selected` découplé |
| Append stale `[...draft.products, next]` | `replaceProducts` / `appendProduct` via `setDraft` fonctionnel |
| Remount « corrigeait » | Plus nécessaire — sync immédiate sur `draft.products` |
| Race autosave | `draftRef` + `draftEpochRef` ; payload depuis ref ; patch id seulement ; re-schedule si epoch avancé |

## STOP

Pas de F1.4. Pas de commit.
