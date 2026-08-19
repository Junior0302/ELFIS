/** Centralized overlay z-index tokens (CSS + TS). */

export const OVERLAY_Z = {
  base: 1,
  sticky: 20,
  dropdown: 40,
  popover: 50,
  tooltip: 55,
  drawer: 70,
  dialog: 80,
  critical: 90,
} as const

export type OverlayZLayer = keyof typeof OVERLAY_Z

export const OVERLAY_Z_CSS_VARS = {
  base: '--z-base',
  sticky: '--z-sticky',
  dropdown: '--z-dropdown',
  popover: '--z-popover',
  tooltip: '--z-tooltip',
  drawer: '--z-drawer',
  dialog: '--z-dialog',
  critical: '--z-critical-overlay',
} as const

export const OVERLAY_ROOT_ID = 'elfis-overlay-root'
