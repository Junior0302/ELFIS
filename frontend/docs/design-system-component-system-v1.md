# ELFIS Design System — Component System V1 (E1.4)

## Objectif

Fournir des composants transversaux neutres (layout, cards, formulaires de base) branchés sur `--pilot-*` et les tokens fondation, sans Dialog.

## Dialog — reporté à E1.4.1

**Aucun composant Dialog n’est livré dans E1.4.**

### Audit des overlays existants

| Surface | Implémentation | Focus trap | Escape | Focus restore | Scroll lock | Portal | Notes a11y |
|---|---|---|---|---|---|---|---|
| `DecisionDetailPage` ConfirmDialog | `.modal-backdrop` + `role="dialog"` | Non | Non | Non | Non | Non | Pas de focus initial ; backdrop click ferme |
| `SalesDocPreviewModal` | backdrop = `role="dialog"` (sur le wrapper) | Non | Non | Non | Non | Non | Rôle sur mauvais nœud |
| `TrialActivationState` tour | `fi-tour-overlay` dialog | Partiel | Non | Non | Non | Non | Close button focusable |
| `AuditEventDetailsDrawer` | drawer backdrop | Non | Oui | Non (focus close only) | Non | Non | Escape OK |
| `PlatformDocumentsPage` legal hold | `platform-modal` | Non | ? | Non | Non | Non | Minimal |
| `window.confirm` (Clients, Facturation, Banking, Catalogue, …) | Native | N/A | N/A | N/A | N/A | N/A | Non stylable, hors DS |

### Besoins E1.4.1

- Dialog accessible complet (focus trap, Escape, restore, scroll lock, Portal)
- Remplacement progressif de `window.confirm`
- Drawer / overlays dédiés si besoin

## Composants Dashboard transversaux

- `Section`
- `StatCard` (trend ≠ sentiment)
- `MetricCard`
- `QuickActionCard` (lien ou bouton réel)

## Primitives responsive

- `Container` (sm…xl / full)
- `Stack`
- `Inline` (+ `stackOnMobile`)
- `Grid` (1–4 / auto-fit)

## Autres composants V1

`Button`, `Input`, `FormField`, `Badge`, `EmptyState`, `Progress`, `PageHeader`

## Motion tokens

`--motion-duration-{instant,fast,normal,slow}` · `--motion-easing-{standard,emphasized,exit}`  
Utilisés pour hover/focus/skeleton. `prefers-reduced-motion` désactive les transitions DS.

## Tokens fondation

Spacing `--space-1…12` · Radius `--radius-sm…pill` · Shadows `--shadow-sm|md|lg` · Controls `--control-height-*` · Containers `--container-*`

## Migrations pilotes (max 4)

1. **Launch Dashboard** — QuickActionCard, Button, Progress, Badge  
2. **Work Queue** — PageHeader, Section, Badge accent, EmptyState  
3. **Enterprise Setup (nom)** — FormField, Input, Button, Stack  
4. **(inclus Work Queue header)** — PageHeader comme 4ᵉ surface structurelle

StatCard / MetricCard : sandbox uniquement (pas de Dashboard financier).

## Parité ComptaPilot

Boutons = classes `.btn` legacy · tokens fondation calqués sur `--radius` / `--shadow` · accents via `--pilot-*` déjà alignés E1.3.

## Interdictions respectées

Pas de Dialog, Drawer, Popover, DataTable, Charts, Toast system, Framer Motion, etc.

## E1.4.1 prévu

Dialog & Overlay System (accessible).

## E1.5

Non commencé.
