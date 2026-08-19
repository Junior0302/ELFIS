# ELFIS Design System — Quality Gates, Lifecycle, Folder & Code Rules

**Version:** 1.0.0  
**Official gates for ELFIS Design System 1.0**

---

## 1. Component lifecycle

| State | Criteria | Product use |
|-------|----------|-------------|
| **Experimental** | API unstable; incomplete tests/docs/a11y | Prototypes / internal only |
| **Preview** | Usable API; known gaps (sandbox, collision, migration) documented | Allowed with care on new surfaces |
| **Stable** | **All quality gates below pass** | Default for product UI |
| **Legacy** | Pre-DS pattern still in production | Migrate; no new usage |
| **Deprecated** | Stable replacement exists + migration note | Do not use; removal scheduled |
| **Blocked** | Must not ship | Forbidden |

Registry: `src/design-system/governance/componentMaturity.ts`

---

## 2. Quality gate — Stable checklist

A component may become **Stable** only if:

| Gate | Requirement |
|------|-------------|
| ✔ Documentation | Purpose, props, a11y notes |
| ✔ Sandbox | Visible in Theme Sandbox |
| ✔ Responsive | Usable at shell breakpoints; no clipped primary content at 100–150% |
| ✔ Tests | Unit (and interaction if overlay-like) |
| ✔ Accessibility | Focus, keyboard, ARIA as applicable; reduced-motion if animated |
| ✔ Themes | Renders correctly under ProductThemeProvider / pilot tokens |
| ✔ Design review | Visual/token review signed (team process) |
| ✔ Technical review | Code review against contributing + code rules |

**If any gate fails → maturity stays Preview (or Experimental).**

---

## 3. Design review process

```
Idée
  ↓
Prototype
  ↓
Review (design + tech)
  ↓
Sandbox
  ↓
Tests
  ↓
QA (a11y / theme / responsive smoke)
  ↓
Stable (registry update)
  ↓
Release (version bump if public surface warrants it)
```

No shortcut from Prototype → Stable.

---

## 4. Folder governance (official tree)

```
frontend/src/design-system/
  version.ts                 # VERSION / BUILD / DATE / MATURITY
  index.ts                   # public barrel
  branding/                  # product marks / assets helpers
  colors/                    # palettes, gradients (HEX allowed here only)
  components/                # UI primitives
  governance/                # maturity, certification
  overlays/                  # dialogs, drawers, portal, manager
  products/                  # registry, categories, validate
  sandbox/                   # theme sandbox page helpers
  themes/                    # Theme Engine
  tokens/                    # foundation + pilot tokens
  types/

frontend/src/app-launcher/   # App Launcher only (not a second DS)

frontend/docs/               # official markdown contracts
frontend/src/**/*.test.*     # tests (Vitest)
```

### Forbidden parallel structures

- `src/ui-kit/`, `src/components-ds/`, Pilot-local `design-system/` folders  
- Second `overlays/` or `launcher/` packages outside the official paths  
- Ad-hoc `portal.tsx` / `focusTrap.ts` in pages  

Icons: prefer shared branding/assets; if an `icons/` package is added later, it must live under `design-system/` and be documented in a minor release.

---

## 5. Code rules

### Interdictions

| Forbidden | Use instead |
|-----------|-------------|
| ❌ New HEX outside palettes | `colors/palettes.ts` → tokens |
| ❌ New legacy `.btn` in new code | `Button` |
| ❌ New custom dialogs | `Dialog` / `ConfirmDialog` |
| ❌ New portal | `overlays/Portal` + OverlayProvider |
| ❌ New focus trap | overlay focus utils / provider behaviour |
| ❌ New scroll lock | `overlays/utils/scrollLock` |
| ❌ New launcher | `app-launcher` |
| ❌ New product registry | `products/registry.ts` |

### Obligations

| Required | Module |
|----------|--------|
| ✔ Product Registry | `products/` |
| ✔ Theme Engine | `themes/` |
| ✔ Overlay Provider | `overlays/` |
| ✔ Components | `components/` |
| ✔ Tokens | `tokens/` + CSS variables |

---

## 6. Future roadmap (documentation only — not E1.7 scope)

### Design System 1.1

- Visual regression CI  
- axe CI  
- Storybook  
- Charts primitives  

### Design System 1.2

- Motion library  
- DataGrid  
- Rich Editor  

### Design System 2.0

- Multi-brand  
- White-label  
- Native mobile  

No implementation of 1.1+ in this release.
