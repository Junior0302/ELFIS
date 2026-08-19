/**
 * ELFIS Design System — official version (single source of truth).
 * Do not hardcode VERSION elsewhere; import from here or from `design-system`.
 */

export const DESIGN_SYSTEM_NAME = 'ELFIS Design System' as const

/** SemVer string — bump only via release process (see design-system-versioning.md). */
export const VERSION = '1.0.0' as const

/** Monotonic build label for this certified release. */
export const BUILD = 'e1.7-ds-1.0.0' as const

/** ISO date of the 1.0.0 certification. */
export const DATE = '2026-07-31' as const

/**
 * Release maturity of the Design System as a whole (not per-component).
 * Component-level maturity lives in governance/componentMaturity.ts.
 */
export const MATURITY = 'stable' as const

export type DesignSystemVersionInfo = {
  name: typeof DESIGN_SYSTEM_NAME
  version: typeof VERSION
  build: typeof BUILD
  date: typeof DATE
  maturity: typeof MATURITY
}

export const DESIGN_SYSTEM_VERSION: DesignSystemVersionInfo = {
  name: DESIGN_SYSTEM_NAME,
  version: VERSION,
  build: BUILD,
  date: DATE,
  maturity: MATURITY,
}
