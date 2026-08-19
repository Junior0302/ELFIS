# ELFIS Design System — Migration Roadmap V1 (E1.6)

**Principle:** Nothing is deleted automatically. Legacy remains until replacement coverage is proven.

```
Legacy → Migration → Suppression → Nettoyage → Version finale
```

---

## 1. Legacy inventory

### 1.1 CSS / helpers

| Legacy | Replacement ELFIS | Remaining migration | Priority | Risk |
|--------|-------------------|---------------------|----------|------|
| `.btn` / `.btn.*` | `Button` (`ds-button` + parity classes) | Hundreds of call sites | P0 | Medium — visual parity must hold |
| `.badge` | `Badge` | Widespread | P1 | Low |
| Legacy card classes | `StatCard` / `MetricCard` / `QuickActionCard` / `Section` | Dashboard & lists | P1 | Medium |
| Legacy dialog / modal CSS | `Dialog` / `Drawer` | Scattered | P0 | High — a11y |
| Legacy form layouts | `FormField` + `Input` | Enterprise setup + pages | P1 | Medium |
| Legacy inputs (raw) | `Input` | Forms | P1 | Low |
| Hardcoded HEX in `index.css` | Semantic / pilot tokens | Large | P0 | High — theme drift |
| Legacy `--forest` / `--ink` | Pilot semantic tokens | Theme dual-write | P1 | Medium |
| Spacing/radius literals | `--space-*` / `--radius-*` | CSS churn | P2 | Low |
| Magic `z-index` | `--z-*` | Overlays mostly done | P2 | Low |
| `window.confirm` | `ConfirmDialog` | ~16 pages | P0 | High — UX/a11y |
| Local ConfirmDialog copies | DS `ConfirmDialog` | DecisionDetail etc. | P0 | Medium |
| Ad-hoc tooltips/popovers | `Tooltip` / `Popover` | Unknown count | P2 | Medium |

### 1.2 Classification for governance

| Item | Status |
|------|--------|
| DS components V1 | Used / Stable or Preview |
| `.btn` in app | Legacy — deprecate new usage (lint later) |
| Dual color CSS vars | Legacy — remove later after migration |
| Unused motion tokens | Used=partial — prune later |
| HEX in `palettes.ts` | Used — source of truth, not legacy |

---

## 2. Roadmap phases

### Phase L0 — Freeze (done with E1.6)

- Inventory documented  
- Governance maturity registry live  
- No new DS components required for migration  
- **No deletions**

### Phase L1 — Migration (E1.7+)

1. **Confirm / dialog wave** — replace `window.confirm` + local confirms  
2. **Button wave** — new code must use `Button`; codemod optional  
3. **Form wave** — FormField + Input on setup & settings  
4. **Card wave** — dashboard metrics to Stat/Metric/QuickAction  
5. **Color wave** — page HEX → tokens; StatCard trends  

Exit criteria per wave: usage count ↓, tests green, visual check on ComptaPilot.

### Phase L2 — Suppression

Only when:

- Replacement is **Stable**  
- Grep usage of legacy pattern = 0 (or allowlisted)  
- Owner sign-off  

Candidates order: local ConfirmDialog → `window.confirm` → unused CSS helpers → orphan HEX blocks.

### Phase L3 — Nettoyage

- Remove dead CSS in `index.css`  
- Collapse dual token aliases  
- Drop unused motion tokens  
- Sandbox completeness  

### Phase L4 — Version finale

- Design System **2.0** declaration when:  
  - Migration score ≥ 80  
  - Legacy control ≥ 70  
  - Lint bans for `.btn` / raw HEX (outside palettes)  
  - Axe gate on sandbox  

---

## 3. Suggested sequencing (no auto-start)

| Order | Workstream | Depends on |
|-------|------------|------------|
| 1 | ConfirmDialog migration | Overlays Stable (done) |
| 2 | Sandbox form primitives | E1.6 docs |
| 3 | Lint: no new `window.confirm` | Policy |
| 4 | Button codemod / incremental | Button Stable |
| 5 | Tokenize remaining HEX hotspots | Theme Engine |
| 6 | Suppress dead CSS | Usage = 0 |
| 7 | Declare DS 2.0 | Scores |

---

## 4. Risk register

| Risk | Mitigation |
|------|------------|
| Visual regression on `.btn` swap | Keep class parity wrappers |
| Focus bugs on dialog migration | Reuse OverlayProvider patterns + RTL tests |
| Theme break on HEX removal | Migrate via semantic tokens first |
| Scope creep into new components | Governance: E1.6 forbids; E1.7 scoped |

---

## 5. Explicit non-actions (E1.6)

- No automatic file deletion  
- No mass codemod without review  
- No E1.7 implementation in this milestone  
- No Pilot SPA scaffolding for Sales/Doc/HR/…

---

## 6. Tracking

- Code registry: `componentMaturity.ts`  
- Scores: `DESIGN_SCORE_CATEGORIES`  
- Docs: this file + QA + governance + accessibility  

Update this roadmap when a migration wave completes (usage counts + score deltas).
