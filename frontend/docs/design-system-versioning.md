# ELFIS Design System — Versioning

**Current release:** 1.0.0  
**Source of truth:** `frontend/src/design-system/version.ts`  
(`VERSION`, `BUILD`, `DATE`, `MATURITY`, `DESIGN_SYSTEM_VERSION`)

Never hardcode the version string in multiple places — import from `version.ts` / `design-system`.

---

## SemVer

| Level | When to bump | Examples |
|-------|----------------|----------|
| **Major** (x.0.0) | Breaking API or architectural contract change | Rename public exports, remove Stable API, change token contract incompatibly |
| **Minor** (1.x.0) | Backward-compatible features | New Stable component, new token family, new quality gate tooling |
| **Patch** (1.0.x) | Backward-compatible fixes | A11y fix, bugfix, docs-only correction that clarifies behavior without API change |

Component maturity changes alone do **not** require a major bump unless a public API breaks.

---

## Release process

1. Update `version.ts` (`VERSION`, `BUILD`, `DATE`, `MATURITY` if needed)  
2. Write / update Release Notes under `frontend/docs/`  
3. Ensure certification matrix still accurate (`governance/certification.ts`)  
4. Run Design System + Theme + Overlay + Launcher + Components tests  
5. Run TypeScript + production build  
6. Tag / announce only after gates pass  

---

## Maturity vs version

| Concept | Scope |
|---------|--------|
| `MATURITY` in `version.ts` | Whole Design System release (e.g. `stable` for 1.0) |
| Component maturity registry | Per-component Experimental → Deprecated |

A **stable** DS release may still contain **Preview** components.

---

## Release Notes V1.0

See [design-system-release-notes-v1.0.md](./design-system-release-notes-v1.0.md).

---

## Future versions (no implementation in E1.7)

| Version | Intent |
|---------|--------|
| **1.1** | Visual regression CI, axe CI, Storybook, Charts primitives |
| **1.2** | Motion library, DataGrid, Rich Editor |
| **2.0** | Multi-brand, white-label, native mobile |

Details in certification / roadmap sections of the 1.0 docs set.
