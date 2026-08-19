# 10 — Implementation report F1.3.1 — GO / NO GO

## Verdict : **GO** (Pass 1)

Pass 1 UX zero friction livré. Aucun commit.

## Correctif F1.3.1.1 — Full Focus

Voir [16-full-focus-implementation-report.md](./16-full-focus-implementation-report.md) — **GO**. Composer n’est plus limité à masquer la nav Facturation : shell Compta masqué jusqu’à sortie explicite.

## Critères Pass 1 (20 points brief)

| # | Critère | Statut |
|---|---------|--------|
| 1 | Audit runtime écrit (01) | GO |
| 2 | Nav sans « Nouveau document » (4 espaces) | GO |
| 3 | Route Composer conservée (deep link `?type=`) | GO |
| 4 | Documents = entrée + CTA unique | GO |
| 5 | Pop-in type (Dialog DS, a11y) | GO |
| 6 | Composer freeform (pas sidebar 10 steps) | GO |
| 7 | Progression légère données réelles | GO |
| 8 | Layout édition / preview sticky | GO |
| 9 | CustomerPicker closed-by-default | GO |
| 10 | ProductPicker closed-by-default | GO |
| 11 | Ligne libre sans ouvrir picker | GO |
| 12 | Dedup validations / insights | GO |
| 13 | Purge copy technique UI | GO |
| 14 | Focus mode (nav secondaire masquée) | GO → étendu F1.3.1.1 |
| 15 | Header premium actions limitées | GO |
| 16 | PDF preview existant (zoom/fullscreen) | GO |
| 17 | Exit confirm si draft local | GO |
| 18 | Responsive CSS + pop-in mobile | GO |
| 19 | Tests UXF01–40 + MR01–30 doc | GO |
| 20 | `npm run build` + tests verts | GO |

## Hors scope respecté

APIs, tables, calculs, Vault, mailer, PDF engine, Search Engine, Resource System, logique comptable, InventoryPilot, nouveaux frameworks : **non touchés** (UI / wiring uniquement).

## Preuves tests

- `facturation-ux-review.test.tsx` : UXF01–40
- `facturation-full-focus.test.tsx` : FF01–40 (F1.3.1.1)
- `npm run build` : OK

## Manuel restant

MR01–MR30 (`09`) + MF01–MF25 (`15`) — **À tester manuellement**.

## STOP

Phases F1.3.1 + F1.3.1.1 terminées. **Ne pas commencer F1.4.**
