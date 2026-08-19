# ELFIS Design System — QA Report V1 (E1.6)

**Date:** 2026-07-26 (audit window)  
**Type:** Certification audit — accessibility, visual coherence, tokens, components, legacy  
**Non-goal:** New components; automatic deletions

---

## 1. Executive verdict

The Design System is **functionally industrializable** for ComptaPilot shells and new surfaces. Global design score lands in the **mid-70s /100** — strong architecture/tests, weak migration/legacy control.

| Deliverable | Status |
|-------------|--------|
| Architecture | Strong |
| A11y (DS layer) | Good after E1.6 FormField/Input |
| Responsive shell | Good; page debt remains |
| Theming / multi-pilot sandbox | Good for Compta/Sales/Doc themes |
| Component API | Good; sandbox gaps |
| Legacy debt | High — by design not deleted |

---

## 2. Design Score (evidence-based)

Source: `DESIGN_SCORE_CATEGORIES` / `globalDesignScore()`.

| Category | /100 | Rationale (short) |
|----------|------|-------------------|
| Architecture | 88 | Registry, Theme Engine, overlays, launcher separated |
| Accessibilité | 78 | Overlays/Launcher solid; FormField/Input fixed; legacy modals remain |
| Responsive | 78 | Shell 1024 + Drawer; ad-hoc breakpoints in `index.css` |
| Theming | 80 | Pilot tokens live; dual `--forest`/`--ink` legacy |
| Components | 82 | V1 complete + tested; sandbox gaps |
| Motion | 75 | Tokens + reduced-motion; unused instant/exit |
| Performance | 84 | Light launcher; no Sales/Doc SPA bundles |
| Documentation | 85 | E1.1–E1.6 docs set |
| Tests | 86 | ~139 DS + launcher tests (jsdom RTL overlays) |
| Migration | 48 | Hundreds of `.btn` / confirm usages |
| Legacy control | 42 | `index.css` ~213 HEX; dual systems |

**Global ≈ 75 /100** (mean of 11 categories).

---

## 3. Global audit findings

### 3.1 Hardcoded colors

| Location | Approx. HEX hits | Action |
|----------|------------------|--------|
| `src/index.css` | ~213 | Legacy; migrate gradually |
| `design-system/colors/palettes.ts` | ~110 | Intentional palette source |
| `app-launcher/launcher.css` | ~27 | Review → pilot tokens where possible |
| Pages / charts | Scattered | Product debt |

### 3.2 Typography / spacing / radius / shadows

Foundation tokens present (`--space-*`, `--radius-*`, `--shadow-*`, `--motion-*`, containers). Inconsistencies:

- Mixed rem usage vs legacy px in `index.css`
- Card radii not always via `--radius-*` on legacy cards
- Shadow elevation inconsistently applied outside DS cards

### 3.3 Components surveyed

| Surface | Finding |
|---------|---------|
| Buttons | DS `Button` stable; app still dominated by `.btn` |
| Inputs | DS Input OK; legacy forms remain |
| Cards | Stat/Metric/QuickAction OK; legacy card classes remain |
| Badges | DS + legacy `.badge` coexistence |
| Empty / Progress / Sections | DS present; underused in pages |
| Overlays | Solid; ConfirmDialog migration incomplete |
| Launcher / Topbar / Sidebar | Launcher certified; shell CSS mixed |
| Enterprise Setup / Dashboard / Work Queue | Partially on tokens; not fully DS components |
| Documents / Facturation / Clients / Settings | Mixed legacy |
| Sandbox | Themes for Compta/Sales/Doc (+ HR/Legal palettes); missing Input/FormField/EmptyState/Progress/PageHeader previews |

### 3.4 Visual QA — pilot themes

Compared Theme Sandbox surfaces (token application, not full SPA):

| Pilot theme | Align / space / radius | Hover / focus / disabled | Theme switch break? |
|-------------|------------------------|---------------------------|---------------------|
| ComptaPilot | Pass DS samples | Pass | No |
| SalesPilot | Pass DS samples | Pass | No |
| DocPilot | Pass DS samples | Pass | No |
| HRPilot | Palette only | N/A product UI | N/A |
| LegalPilot | Palette only | N/A product UI | N/A |

**Rule:** No DS component must break when changing pilot theme. Verified for registered sandbox components.

### 3.5 Duplications / unused

- Dual button systems (`.btn` vs `ds-button` wrapping `.btn`)
- Dual confirm UX (`window.confirm` vs `ConfirmDialog`)
- Motion tokens unused: instant / some exit durations
- Popover vs launcher Popover usage patterns diverge slightly (acceptable)

---

## 4. Token matrix

| Token family | Used | Deprecated | Remove later |
|--------------|------|------------|--------------|
| `--space-*` | Yes (DS + some pages) | — | Legacy px spacers in CSS |
| `--radius-*` | Yes | — | Hardcoded `8px`/`12px` in index |
| `--shadow-*` | Partial | — | Box-shadow literals |
| `--motion-*` | Partial | — | Unused instant/exit |
| Pilot semantic colors | Yes | — | — |
| Legacy `--forest` / `--ink` / HEX | Heavy | Mark as legacy | After page migration |
| Component tokens (`--ds-*`) | Yes | — | — |
| Z-index `--z-*` | Yes (overlays) | — | Magic z-index in legacy |

---

## 5. Component Health (method)

`healthScore(component)` from documentation, tests, sandbox, and 0–2 axes (API, a11y, responsive, theme, performance).

Typical Stable fully sandboxed components score **~100**.  
Preview without sandbox (EmptyState, Progress, PageHeader, Input, FormField) score **~92** (sandbox bit missing).  
Tooltip/Popover lower on responsive/a11y axes (~85–90).

Full table: generate from registry in runtime / governance tests — do not hardcode divergent numbers in docs.

---

## 6. Design Review

### Strengths

- Clear module boundaries (tokens → theme → components → overlays → launcher)
- Overlay orchestrator (stack, priority, Escape, auth close-all)
- Evidence-backed governance registry
- Strong test density for DS layer

### Weaknesses

- App-wide migration lag
- Dual CSS color systems
- Sandbox incomplete for form primitives
- No CI visual/a11y regression gate

### Debt

- ~213 HEX in `index.css`
- Widespread `.btn` / `.badge`
- `window.confirm` on ~16 pages
- Local ConfirmDialog (e.g. decision detail)
- StatCard trend HEX

### Priorities (E1.7 candidates — not started)

1. Wire axe or equivalent on DS sandbox  
2. ConfirmDialog migration wave  
3. Sandbox: Input, FormField, EmptyState, Progress, PageHeader  
4. Tokenize StatCard trends  
5. Deprecate new `.btn` usage via lint rule  

### Blockers

- None for ComptaPilot Design Ready  
- Sales/Doc SPA absence blocks full Pilot Design Ready  

### Opportunities / Quick wins

- Lint: ban raw HEX outside palettes  
- ESLint rule: prefer `ConfirmDialog` over `window.confirm`  
- Add missing sandbox sections  

### Architecture / Vision

Keep **one** DS. Migrate pages inward. Suppress legacy only after replacement + usage = 0. Multi-pilot themes stay token-driven; product UIs ship when routes exist.

---

## 7. Pilot Readiness (detail)

See governance doc + `PILOT_READINESS`. ComptaPilot Design Ready; Sales/Doc Partially Ready; others Not Ready.

---

## 8. Tests & build (E1.6 gate)

Run (frontend):

- Design System / Theme / Components / Overlay / Launcher / Governance suites  
- `tsc` / production `build`

Results recorded at milestone close in the agent report (section M).
