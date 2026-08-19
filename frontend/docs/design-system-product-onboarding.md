# ELFIS Design System — Product Onboarding Guide

**Version:** 1.0.0  
**Purpose:** Official checklist to add a new Pilot to ELFIS  
**Constraint:** This guide documents the process. **Do not create a new Pilot in E1.7.**

---

## Overview

A Pilot is a product entry in the **Product Registry**, with palette, branding, theme tokens, launcher presence, and (when ready) routes.

```
Registry → Palette → Branding → Tokens → Theme → Launcher → Routes → Docs → Tests → Sandbox → QA
```

---

## Checklist

| # | Step | Done when |
|---|------|-----------|
| 1 | **Product Registry** | Product id, name, category, status (`active` / `coming_soon` / …) registered in `products/registry.ts` + validation |
| 2 | **Palette** | Colors defined in `colors/palettes.ts` (HEX only here) |
| 3 | **Branding** | Marks/assets wired via `branding/` as needed |
| 4 | **Tokens** | Pilot semantic tokens resolve via Theme Engine |
| 5 | **Launcher** | Entry visible with correct status; no fake routes for `coming_soon` |
| 6 | **Routes** | SPA routes exist **only** when product is navigable; entry route helper updated |
| 7 | **Theme** | Theme resolves/applies without fallback errors for the product id |
| 8 | **Documentation** | Short product identity note + any shell specifics |
| 9 | **Tests** | Registry/theme/launcher tests cover the new id |
| 10 | **Sandbox** | Theme Sandbox can preview the pilot theme |
| 11 | **QA** | Contrast/focus smoke on sandbox; no theme breakage vs ComptaPilot samples |

---

## Rules

- **One registry** — never a second product dictionary  
- **One Theme Engine** — never Pilot-local CSS variable injectors  
- **One Launcher** — never a second app switcher  
- **No SalesPilot / DocPilot SPA scaffolding in E1.7** — onboarding is documentation only  
- Prefer `coming_soon` until routes and shell are real  

---

## Minimal code touchpoints (reference)

```
frontend/src/design-system/products/registry.ts
frontend/src/design-system/colors/palettes.ts
frontend/src/design-system/tokens/pilotTokens.ts
frontend/src/design-system/themes/*
frontend/src/app-launcher/*
frontend/src/design-system/sandbox/ThemeSandboxPage.tsx
```

---

## Readiness levels (post-onboarding)

| Level | Meaning |
|-------|---------|
| Design Ready | Theme + launcher + navigable shell using DS |
| Partially Ready | Theme/sandbox and/or launcher chip; no full SPA |
| Not Ready | Registry (± palette) only |

See `PILOT_READINESS` in governance and [design-system-certification-v1.md](./design-system-certification-v1.md).
