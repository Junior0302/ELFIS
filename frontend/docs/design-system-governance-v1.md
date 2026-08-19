# ELFIS Design System — Governance V1 (E1.6)

**Status:** Active registry  
**Source of truth (code):** `frontend/src/design-system/governance/componentMaturity.ts`  
**Export:** `@/design-system` → maturity helpers + registries

---

## 1. Purpose

Industrialize the Design System without inventing new components. Governance answers:

- What is **allowed** in product UI?
- What is **stable** vs **legacy**?
- What is the **health** of each component?
- How ready is each **Pilot**?

---

## 2. Maturity levels

| Level | Meaning | Product use |
|-------|---------|-------------|
| **Experimental** | API may change; limited tests | Sandbox / internal only |
| **Preview** | Usable; gaps (sandbox, a11y, collision) documented | Feature flags / new surfaces OK with care |
| **Stable** | Documented, tested, theme-safe | Default for product UI |
| **Legacy** | Pre-DS patterns still in production | Migrate; no new usage |
| **Deprecated** | Replacement exists; removal planned | Do not use |
| **Blocked** | Must not ship | Forbidden |

Current registry: no `blocked` entries. Legacy lives mostly **outside** the DS package (`index.css`, `.btn`, `window.confirm`).

---

## 3. Component metadata (required fields)

Every registry entry carries:

| Field | Description |
|-------|-------------|
| `version` | Component API version (currently `1.0`) |
| `owner` | Usually `design-system` |
| `lastChange` | Milestone id (`E1.4`, `E1.4.1`, `E1.5`, `E1.6`) |
| `documentation` | Doc exists in `frontend/docs` or module README |
| `tests` | Unit/integration coverage |
| `sandbox` | Visible in Theme Sandbox |
| `migrationComplete` | App-wide replacement done |
| `api` / `accessibility` / `responsive` / `theme` / `performance` | 0–2 evidence scores |
| `maturity` | One of the levels above |

**Health score** = weighted sum of booleans + 0–2 axes, normalized `/100` via `healthScore()`.

Do **not** invent scores: change criteria in code when evidence changes, then re-run governance tests.

---

## 4. Registry snapshot (E1.6)

| Component | Maturity | Sandbox | Migration | Notes |
|-----------|----------|---------|-----------|-------|
| Button | Stable | Yes | Incomplete | Still wraps `.btn` |
| Input | Stable | No | Incomplete | `:focus-visible` E1.6 |
| FormField | Stable | No | Incomplete | aria wire E1.6 |
| Badge | Stable | Yes | Incomplete | |
| EmptyState | Preview | No | Incomplete | |
| Progress | Preview | No | Incomplete | |
| PageHeader | Preview | No | Incomplete | |
| Section | Stable | Yes | Incomplete | |
| StatCard | Stable | Yes | Incomplete | Trend HEX debt |
| MetricCard | Stable | Yes | Incomplete | |
| QuickActionCard | Stable | Yes | Incomplete | |
| Container / Stack / Inline / Grid | Stable | Yes | Complete (layout) | |
| Dialog / ConfirmDialog / Drawer | Stable | Yes | Incomplete | |
| Tooltip / Popover | Preview | Yes | Incomplete | Option B CSS |
| OverlayProvider | Stable | No | Complete | |
| AppLauncher | Stable | Yes | Complete (shell) | |
| ProductMark | Preview | No | Complete | |

---

## 5. Design Score categories

Defined in `DESIGN_SCORE_CATEGORIES` (each `/100` + rationale):

Architecture · Accessibility · Responsive · Theming · Components · Motion · Performance · Documentation · Tests · Migration · Legacy control

**Global** = arithmetic mean via `globalDesignScore()`.

See `design-system-qa-report-v1.md` for the scored audit narrative.

---

## 6. Pilot readiness

| Product | Readiness | Why (short) |
|---------|-----------|-------------|
| ComptaPilot | Design Ready | Active runtime, theme, launcher, migrated shells |
| ELFIS Core | Partially Ready | Platform identity; no workspace product shell |
| SalesPilot | Partially Ready | Theme + sandbox; `coming_soon`; no SPA |
| DocPilot | Partially Ready | Theme + sandbox; `coming_soon`; no SPA |
| HR / Legal / Inventory / Marketing / Project / Support | Not Ready | Registry (± palette) only |

Source: `PILOT_READINESS` in code.

---

## 7. Design Review rules

Any change to a **Stable** component must update:

1. `lastChange` milestone  
2. Tests  
3. Docs if API/behavior changes  
4. Sandbox if visual  

Preview → Stable when: docs + tests + sandbox + a11y ≥ 2 + no known blockers.

Legacy → Deprecated only when DS replacement is Stable **and** migration guide exists.

**Never auto-delete** legacy CSS in governance milestones (E1.6).

---

## 8. Ownership

| Area | Owner |
|------|-------|
| Tokens / Theme Engine | design-system |
| Components / overlays | design-system |
| App Launcher | design-system + shell |
| Product page migration | product squads (ComptaPilot first) |
| Governance registry | design-system |

---

## 9. Related docs

- `design-system-accessibility-v1.md`
- `design-system-qa-report-v1.md`
- `design-system-migration-roadmap-v1.md`
- Prior: brand, identity, theme engine, semantic migration, components, overlays, launcher
