# ELFIS Design System — Accessibility V1 (E1.6)

**Status:** Certified audit (not a new component release)  
**Scope:** Design System + overlays + App Launcher + critical form primitives  
**Non-goal:** New UI components; automatic legacy deletion

---

## 1. Summary

Accessibility for the industrial Design System layer is **solid on overlays and launcher**, and **improved on FormField / Input** in E1.6. Residual risk sits in **legacy page surfaces** (`window.confirm`, ad-hoc modals, dense `index.css` HEX).

| Area | Verdict |
|------|---------|
| Dialog / ConfirmDialog / Drawer | Pass — focus trap, Escape, ARIA, scroll lock |
| Tooltip / Popover | Pass with caveats — CSS placement, no Floating UI |
| App Launcher | Pass — desktop Popover / mobile Drawer, keyboard |
| Button / Badge / Progress / EmptyState | Pass (DS) |
| FormField + Input | Pass after E1.6 wiring (`aria-describedby`, `:focus-visible`) |
| Legacy pages / `.btn` / native confirm | Fail / partial — migration incomplete |

---

## 2. Automated checks (evidence)

### 2.1 Overlays

Verified in overlay unit/integration tests:

| Criterion | Status | Notes |
|-----------|--------|-------|
| `role="dialog"` / alertdialog | OK | Dialog, ConfirmDialog |
| `aria-modal` | OK | Top overlay |
| `aria-labelledby` / `aria-describedby` | OK | Title / description ids |
| Focus trap | OK | Top-of-stack only |
| Escape closes top | OK | Manager priority |
| Focus restore | OK | On unmount |
| Scroll lock ref-count | OK | Nested overlays |
| Portal root `#elfis-overlay-root` | OK | Sync create (no focus loss) |
| `prefers-reduced-motion` | OK | Overlay CSS |

### 2.2 App Launcher

| Criterion | Status | Notes |
|-----------|--------|-------|
| Trigger `aria-expanded` / `aria-controls` | OK | |
| Keyboard open/close | OK | |
| Escape | OK | Via overlay stack |
| Product cards as buttons | OK | Active / coming_soon / chip |
| Mobile Drawer ≤1024px | OK | Pointer coarse friendly height |

### 2.3 Forms (E1.6 fixes)

| Criterion | Before E1.6 | After E1.6 |
|-----------|-------------|------------|
| FormField `aria-describedby` on control | Not auto-wired | Wired when single valid child |
| FormField `aria-invalid` on error | Missing | Set when `error` present |
| Hint / error ids | Present on text | Linked to control |
| Input focus ring | `:focus` | `:focus-visible` |

### 2.4 Reduced motion

Tokens `--motion-*` + reduced-motion media queries in:

- `overlays.css`
- `components.css` (where animated)
- `launcher.css`

Unused motion tokens (`instant`, exit variants) remain in the token map — see token matrix in QA report.

---

## 3. Zoom & viewport matrix

Manual / CSS-token based expectations (no automated visual regression in CI yet):

| Zoom | Desktop | Tablet | Mobile | Narrow mobile |
|------|---------|--------|--------|---------------|
| 100% | OK shell | OK | OK launcher drawer | OK |
| 125% | OK | OK | OK | Risk: dense tables |
| 150% | OK shell | Risk: topbar crowding | OK | Risk: truncation |
| 200% | Partial — scroll expected | Partial | Partial | Fail risk: platform tables |
| 400% | Partial — reflow via browser | Partial | Partial | Fail risk: legacy grids |

**Pointer:**

- Fine: hover states on DS cards / launcher
- Coarse: launcher uses Drawer; hit targets ≥ ~40px on DS buttons via legacy `.btn` sizing

**Rule for E1.6:** No DS component may lose *readable* text at 200% on a 1280px desktop. Legacy financial tables may require horizontal scroll (accepted debt).

---

## 4. WCAG contrast

| Surface | Source | Status |
|---------|--------|--------|
| Pilot semantic text/bg | Theme Engine tokens | Pass intent (semantic pairs) |
| Overlay surface / text | `--surface` / `--text` | Pass intent |
| StatCard trend HEX | Hardcoded up/down colors | **Debt** — verify AA on both themes |
| Legacy `index.css` HEX (~213 hits) | Ad-hoc | **Debt** — not certified per-pair |

Automated contrast tooling (axe / playwright) is **not** wired in CI yet — priority E1.7.

---

## 5. Screen reader & ARIA inventory

| Pattern | ARIA | Owner |
|---------|------|-------|
| Dialog | labelledby, describedby, modal | overlays |
| Drawer | dialog + labelledby | overlays |
| Tooltip | describedby when open | overlays |
| Popover | expanded/controls on trigger | overlays |
| Progress | `role="progressbar"` + valuemin/max/now | components |
| Skeleton / loading cards | `aria-busy` | StatCard etc. |
| Tabs (app pages) | Mixed legacy | **Debt** |
| Links vs buttons | DS Button = button; launcher cards = button | OK DS |

---

## 6. Known gaps (do not start E1.7 here)

1. No axe/playwright a11y gate in CI  
2. ~16+ pages still use `window.confirm`  
3. Local ConfirmDialog variants outside DS  
4. Sandbox gaps: Input, FormField, EmptyState, Progress, PageHeader  
5. Popover not a full menu keyboard model  
6. Tooltip Option B — collision / viewport clipping possible  
7. Dense platform tables at 200–400% zoom  

---

## 7. Acceptance for E1.6

- [x] Overlay + Launcher a11y documented and tested  
- [x] FormField / Input gaps closed in DS  
- [x] Reduced motion respected on DS motion surfaces  
- [x] Residual a11y debt listed for E1.7 (tooling + legacy migration)  
