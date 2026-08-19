# ELFIS Design System — Contributing Guide

**Version:** 1.0.0  
**Audience:** Frontend developers adding or changing Design System surfaces

---

## 1. Before you start

1. Read the [Manifesto](./design-system-manifesto.md)  
2. Read [Quality Gates](./design-system-quality-gates.md)  
3. Check maturity in `src/design-system/governance/componentMaturity.ts`  
4. Confirm there is **no** existing component that already solves the need  

**Do not** create a parallel folder outside `src/design-system` (or `src/app-launcher` for launcher).

---

## 2. How to create a component

### Location

```
frontend/src/design-system/components/MyComponent.tsx
frontend/src/design-system/components/components.css   # shared styles
frontend/src/design-system/components/index.ts         # export
```

### Steps

1. Define a typed props API (no `any`)  
2. Use tokens (`var(--space-*)`, `--radius-*`, `--pilot-*`, semantic colors) — **no new HEX** outside `colors/palettes.ts`  
3. Prefer composition with `Container` / `Stack` / `Inline` / `Grid`  
4. Export from `components/index.ts` and public `design-system/index.ts` (via components barrel)  
5. Start maturity at **Experimental** or **Preview** in the governance registry  
6. Add unit tests  
7. Add sandbox section when visually meaningful  
8. Document in `frontend/docs/` or extend an existing component doc  

### Overlays

Use `Dialog`, `ConfirmDialog`, `Drawer`, `Tooltip`, `Popover` from `design-system/overlays`.  
**Forbidden:** new portal root, focus trap, scroll lock, or custom modal stack.

### Launcher / Registry / Theme

Extend existing modules — do not fork.

---

## 3. Mandatory checklist (every new or changed component)

| # | Check | Required |
|---|-------|----------|
| 1 | Typed public API | Yes |
| 2 | Tokens only (no rogue HEX / magic z-index) | Yes |
| 3 | Keyboard + visible focus | Yes |
| 4 | ARIA roles/labels as needed | Yes |
| 5 | `prefers-reduced-motion` respected if animated | Yes |
| 6 | Works under ProductThemeProvider (Compta + ≥1 other pilot theme if sandbox) | Yes |
| 7 | Responsive at shell breakpoints | Yes |
| 8 | Unit tests | Yes |
| 9 | Sandbox preview (for visual components) | For Preview→Stable |
| 10 | Docs updated | Yes |
| 11 | Registry maturity entry | Yes |
| 12 | No new `.btn` / custom dialog / second launcher | Yes |

---

## 4. Accessibility

- Prefer semantic HTML  
- Wire `aria-*` for composite widgets  
- Form controls: label + `aria-describedby` for errors/hints (see `FormField`)  
- Focus: `:focus-visible`, restore focus on overlay close  
- Never remove outlines without a visible replacement  

Details: [design-system-accessibility-v1.md](./design-system-accessibility-v1.md)

---

## 5. Tests

- Colocate or use `frontend/src/design-system*.test.*` / package tests  
- Overlays/launcher: RTL + user-event where interaction matters  
- Run relevant Vitest suites before PR  

---

## 6. Sandbox

Theme Sandbox (`ThemeSandboxPage`) is the visual contract surface.  
Add a section for any component that can become **Stable**.

---

## 7. Documentation

Minimum: purpose, props, examples, a11y notes, maturity.  
Link from release notes when shipping a minor/major.

---

## 8. Responsive & Theme

- Layout via tokens and existing breakpoints (shell ~1024 for launcher Drawer)  
- No Pilot-specific hardcoded colors in components — use CSS variables from Theme Engine  

---

## 9. When a component may become **Stable**

All quality gates pass (see quality-gates doc):

- documentation ✔  
- sandbox ✔  
- responsive ✔  
- tests ✔  
- accessibility ✔  
- themes ✔  
- design review ✔  
- technical review ✔  

Otherwise it stays **Preview** (or **Experimental** if API unstable).

---

## 10. When it stays **Experimental**

- API likely to change  
- Incomplete a11y or theme coverage  
- No tests or sandbox  
- Used only in prototypes  

---

## 11. Code rules (summary)

**Forbidden**

- New HEX outside palettes  
- New legacy `.btn` usage in new code  
- Custom dialogs / portals / focus traps / scroll locks  
- Second launcher or second product registry  

**Required**

- Product Registry  
- Theme Engine  
- Overlay Provider  
- DS Components + Tokens  

Full rules: [design-system-quality-gates.md](./design-system-quality-gates.md) § Code Rules & Folder Governance.
