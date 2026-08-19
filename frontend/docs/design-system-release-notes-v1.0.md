# ELFIS Design System — Release Notes v1.0.0

**Name:** ELFIS Design System  
**Version:** 1.0.0  
**Build:** `e1.7-ds-1.0.0`  
**Date:** 2026-07-31  
**Maturity:** stable  

Source: `frontend/src/design-system/version.ts`

---

## Highlights

Official certification of **ELFIS Design System 1.0** as the unique UI standard for ELFIS Core and Pilots.

This release is primarily **governance and documentation**. It introduces **no intentional visual redesign** of product UI.

---

## Included (E1.1 → E1.7)

| Area | Milestone |
|------|-----------|
| Brand Foundation | E1.1 |
| Product Identity | E1.1.1 |
| Theme Engine | E1.2 |
| Semantic Theme Migration | E1.3 |
| Component System | E1.4 |
| Overlay System + Orchestrator | E1.4.1 |
| App Launcher | E1.5 |
| Accessibility / QA / Governance | E1.6 |
| Versioning, manifesto, gates, certification | E1.7 |

---

## What 1.0.0 certifies

- Single architecture under `src/design-system` (+ `app-launcher`)  
- Product Registry + Theme Engine as mandatory infrastructure  
- Overlay Provider as the only overlay stack  
- Component maturity registry + health scores  
- Official docs: manifesto, contributing, versioning, onboarding, quality gates, certification  

---

## What 1.0.0 does **not** claim

- Complete elimination of legacy (`.btn`, HEX in `index.css`, `window.confirm`)  
- Full Design Ready status for SalesPilot / DocPilot / other Pilots  
- Visual regression or axe CI (planned 1.1)  
- New Pilot SPA modules  

---

## Developer-facing API note

Import version metadata from the package barrel:

```ts
import { VERSION, BUILD, DATE, MATURITY, DESIGN_SYSTEM_VERSION } from '@/design-system'
// or relative: from './design-system'
```

Do not duplicate version strings in pages or configs.

---

## Upgrade / adoption

1. New UI → DS components + tokens  
2. Dialogs → Overlay system  
3. Product switch → App Launcher  
4. New Pilot → [Product Onboarding](./design-system-product-onboarding.md)  

Migration waves remain tracked in [design-system-migration-roadmap-v1.md](./design-system-migration-roadmap-v1.md).

---

## Next (not started)

- **1.1** — CI visual + axe, Storybook, charts  
- Pilot product builds (SalesPilot, DocPilot, …) are **out of scope** for this release note  

---

## Certification statement

**ELFIS Design System 1.0 is certified.**
