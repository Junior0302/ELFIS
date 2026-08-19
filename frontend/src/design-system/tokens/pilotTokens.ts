/**
 * Semantic Pilot tokens (E1.2) — camelCase intentions, not CSS names.
 * CSS mapping lives in themes/cssVariables.ts only.
 */

import { PRODUCT_PALETTES } from '../colors/palettes'
import { PRODUCT_ACCENT_GRADIENTS } from '../colors/gradients'
import type { ProductId } from '../types'

export type PilotTokens = {
  primary: string
  primaryHover: string
  primaryActive: string
  primaryContrast: string
  secondary: string
  accent: string
  accentSoft: string
  surface: string
  surfaceElevated: string
  surfaceMuted: string
  surfaceHover: string
  border: string
  borderStrong: string
  text: string
  textMuted: string
  focus: string
  success: string
  warning: string
  danger: string
  info: string
  chart1: string
  chart2: string
  chart3: string
  chart4: string
  chart5: string
  chart6: string
  chart7: string
  chart8: string
  gradientStart: string
  gradientEnd: string
}

export const PILOT_TOKEN_KEYS = [
  'primary',
  'primaryHover',
  'primaryActive',
  'primaryContrast',
  'secondary',
  'accent',
  'accentSoft',
  'surface',
  'surfaceElevated',
  'surfaceMuted',
  'surfaceHover',
  'border',
  'borderStrong',
  'text',
  'textMuted',
  'focus',
  'success',
  'warning',
  'danger',
  'info',
  'chart1',
  'chart2',
  'chart3',
  'chart4',
  'chart5',
  'chart6',
  'chart7',
  'chart8',
  'gradientStart',
  'gradientEnd',
] as const satisfies ReadonlyArray<keyof PilotTokens>

export type PilotTokenKey = (typeof PILOT_TOKEN_KEYS)[number]

/** Soften a hex toward white (simple mix) — no color library. */
function mixTowardWhite(hex: string, amount: number): string {
  const raw = hex.replace('#', '')
  if (raw.length !== 6) return hex
  const n = Number.parseInt(raw, 16)
  if (Number.isNaN(n)) return hex
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  const mix = (c: number) => Math.round(c + (255 - c) * amount)
  const toHex = (c: number) => c.toString(16).padStart(2, '0')
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`
}

function mixTowardBlack(hex: string, amount: number): string {
  const raw = hex.replace('#', '')
  if (raw.length !== 6) return hex
  const n = Number.parseInt(raw, 16)
  if (Number.isNaN(n)) return hex
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  const mix = (c: number) => Math.round(c * (1 - amount))
  const toHex = (c: number) => c.toString(16).padStart(2, '0')
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`
}

/**
 * Builds semantic Pilot tokens for a product.
 * Not injected into the DOM by this function alone.
 */
export function buildPilotTokens(productId: ProductId): PilotTokens {
  const colors = PRODUCT_PALETTES[productId]
  const gradient = PRODUCT_ACCENT_GRADIENTS[productId]
  const [c1, c2, c3, c4, c5, c6, c7, c8] = colors.chartPalette
  const primary = colors.primaryColor
  const secondary = colors.secondaryColor
  const accent = colors.accentColor

  // ComptaPilot: exact legacy parity with :root --forest / --forest-deep / --mint / --ink
  const isCompta = productId === 'comptapilot'
  const isElfis = productId === 'elfis-core'
  const primaryHover = isCompta
    ? '#07281E'
    : isElfis
      ? '#102746'
      : mixTowardBlack(primary, 0.08)
  const primaryActive = isCompta ? '#07281E' : isElfis ? '#071629' : mixTowardBlack(primary, 0.16)
  const text = isCompta ? '#10241C' : isElfis ? '#101828' : primary

  return {
    primary,
    primaryHover,
    primaryActive,
    primaryContrast: '#FFFFFF',
    secondary,
    accent,
    accentSoft: isElfis ? '#EAF1FF' : mixTowardWhite(accent, 0.75),
    surface: isElfis ? '#FFFFFF' : secondary,
    surfaceElevated: '#FFFFFF',
    surfaceMuted: isElfis ? '#F8FAFC' : mixTowardWhite(secondary, 0.35),
    surfaceHover: isElfis ? '#EAF1FF' : mixTowardBlack(secondary, 0.04),
    border: isElfis ? '#DDE4EE' : mixTowardWhite(primary, 0.82),
    borderStrong: isElfis ? mixTowardWhite(primary, 0.55) : mixTowardWhite(primary, 0.55),
    text,
    textMuted: isElfis ? '#58657A' : mixTowardWhite(text, 0.45),
    focus: accent,
    success: isElfis ? '#16845B' : '#15803D',
    warning: isElfis ? '#C97816' : '#C4782B',
    danger: isElfis ? '#C83F49' : '#B42318',
    info: isElfis ? '#2764E7' : '#1D4ED8',
    chart1: c1,
    chart2: c2,
    chart3: c3,
    chart4: c4,
    chart5: c5,
    chart6: c6,
    chart7: c7,
    chart8: c8,
    gradientStart: gradient.from,
    gradientEnd: gradient.to,
  }
}

/**
 * @deprecated E1.1 kebab map — use PilotTokens + themeToCssVariables.
 * Kept as named CSS-oriented alias map for older tests.
 */
export type PilotTokenMap = {
  'pilot-primary': string
  'pilot-secondary': string
  'pilot-accent': string
  'pilot-surface': string
  'pilot-surface-hover': string
  'pilot-border': string
  'pilot-ink': string
  'pilot-muted': string
  'pilot-success': string
  'pilot-warning': string
  'pilot-danger': string
  'pilot-info': string
  'pilot-chart-1': string
  'pilot-chart-2': string
  'pilot-chart-3': string
  'pilot-chart-4': string
  'pilot-chart-5': string
  'pilot-chart-6': string
  'pilot-chart-7': string
  'pilot-chart-8': string
}

export type PilotTokenName = keyof PilotTokenMap

/** Legacy-shaped map derived from semantic tokens (compat E1.1 tests). */
export function buildLegacyPilotTokenMap(productId: ProductId): PilotTokenMap {
  const t = buildPilotTokens(productId)
  return {
    'pilot-primary': t.primary,
    'pilot-secondary': t.secondary,
    'pilot-accent': t.accent,
    'pilot-surface': t.surface,
    'pilot-surface-hover': t.surfaceHover,
    'pilot-border': t.border,
    'pilot-ink': t.text,
    'pilot-muted': t.textMuted,
    'pilot-success': t.success,
    'pilot-warning': t.warning,
    'pilot-danger': t.danger,
    'pilot-info': t.info,
    'pilot-chart-1': t.chart1,
    'pilot-chart-2': t.chart2,
    'pilot-chart-3': t.chart3,
    'pilot-chart-4': t.chart4,
    'pilot-chart-5': t.chart5,
    'pilot-chart-6': t.chart6,
    'pilot-chart-7': t.chart7,
    'pilot-chart-8': t.chart8,
  }
}
