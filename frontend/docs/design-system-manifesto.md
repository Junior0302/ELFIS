# ELFIS Design System Manifesto

**Product:** ELFIS Design System  
**Version:** 1.0.0  
**Status:** Official standard  
**Source:** `frontend/src/design-system/version.ts`

---

## Why it exists

ELFIS is a multi-Pilot platform. Without a single Design System, each Pilot invents its own colors, dialogs, buttons, and focus traps. That produces visual drift, accessibility regressions, and unmaintainable CSS.

The Design System exists so that **every Pilot shares one visual and interaction language**, while remaining free to express its own product identity through tokens and branding.

---

## Vision

One industrial Design System for the entire ELFIS suite:

- Predictable UI for users moving between Pilots
- Safe theming via Product Registry + Theme Engine
- Accessible overlays and navigation by default
- Clear rules for contributors and future modules

---

## Values

| Value | Meaning |
|-------|---------|
| **Unity** | One system, not N parallel kits |
| **Clarity** | Tokens and components over ad-hoc CSS |
| **Accessibility** | Keyboard, focus, ARIA, contrast as defaults |
| **Evidence** | Maturity and scores based on real criteria |
| **Restraint** | Prefer reuse over new primitives |
| **Honesty** | Legacy is acknowledged until migrated |

---

## Objectives

1. Certify a **stable 1.0** surface for ComptaPilot and platform shells  
2. Enable new Pilots without forking UI architecture  
3. Make overlays, launcher, and theme **non-negotiable** shared infrastructure  
4. Govern component lifecycle from Experimental to Deprecated  
5. Reduce legacy (`.btn`, HEX, `window.confirm`) through planned migration — not chaos  

---

## Principles

1. **Tokens before paint** — colors/spacing/radius/motion come from tokens  
2. **Registry before theme** — products exist in the Product Registry first  
3. **Components before pages** — pages compose DS primitives  
4. **Overlays before portals** — use OverlayProvider; never invent a second portal/focus trap  
5. **One launcher** — App Launcher is the product switcher  
6. **Document before Stable** — no Stable without docs, tests, sandbox, a11y, theme  
7. **Do not delete legacy blindly** — migrate → suppress → clean  

---

## Hierarchy

```
ELFIS Core
    ↓
Pilot (product identity + theme)
    ↓
Pages (routes & business flows)
    ↓
Components (Design System primitives)
    ↓
Tokens (semantic + foundation)
    ↓
HTML / CSS variables
```

Never invert this stack (e.g. page-local design systems, Pilot-local overlay stacks).

---

## Why a single Design System

| Multi-system world | Single DS world |
|--------------------|-----------------|
| N dialogs, N focus traps | One Overlay system |
| N launchers | One App Launcher |
| N color dictionaries | One Theme Engine + palettes |
| Inconsistent a11y | Shared quality gates |
| Slow Pilot onboarding | Checklist + registry |

**ELFIS Design System 1.0 is the official standard.** Future Pilots and modules must extend it — not replace it.
