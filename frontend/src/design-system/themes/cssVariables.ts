/**
 * Centralized CSS custom property names for Pilot tokens.
 * Do not scatter "--pilot-*" string literals elsewhere.
 */

import type { PilotTokenKey, PilotTokens } from '../tokens/pilotTokens'
import { PILOT_TOKEN_KEYS } from '../tokens/pilotTokens'

/** Semantic token key → CSS variable name. */
export const PILOT_CSS_VAR_BY_TOKEN = {
  primary: '--pilot-primary',
  primaryHover: '--pilot-primary-hover',
  primaryActive: '--pilot-primary-active',
  primaryContrast: '--pilot-primary-contrast',
  secondary: '--pilot-secondary',
  accent: '--pilot-accent',
  accentSoft: '--pilot-accent-soft',
  surface: '--pilot-surface',
  surfaceElevated: '--pilot-surface-elevated',
  surfaceMuted: '--pilot-surface-muted',
  surfaceHover: '--pilot-surface-hover',
  border: '--pilot-border',
  borderStrong: '--pilot-border-strong',
  text: '--pilot-text',
  textMuted: '--pilot-text-muted',
  focus: '--pilot-focus',
  success: '--pilot-success',
  warning: '--pilot-warning',
  danger: '--pilot-danger',
  info: '--pilot-info',
  chart1: '--pilot-chart-1',
  chart2: '--pilot-chart-2',
  chart3: '--pilot-chart-3',
  chart4: '--pilot-chart-4',
  chart5: '--pilot-chart-5',
  chart6: '--pilot-chart-6',
  chart7: '--pilot-chart-7',
  chart8: '--pilot-chart-8',
  gradientStart: '--pilot-gradient-start',
  gradientEnd: '--pilot-gradient-end',
} as const satisfies Record<PilotTokenKey, `--pilot-${string}`>

export type PilotCssVarName = (typeof PILOT_CSS_VAR_BY_TOKEN)[PilotTokenKey]

export const PILOT_CSS_VAR_NAMES: readonly PilotCssVarName[] = PILOT_TOKEN_KEYS.map(
  (key) => PILOT_CSS_VAR_BY_TOKEN[key],
)

/** DOM data-attribute names owned by the Theme Engine. */
export const THEME_DOM_ATTR = {
  product: 'data-product',
  theme: 'data-theme',
  colorScheme: 'data-color-scheme',
} as const

export function tokensToCssVariables(tokens: PilotTokens): Record<PilotCssVarName, string> {
  const out = {} as Record<PilotCssVarName, string>
  for (const key of PILOT_TOKEN_KEYS) {
    out[PILOT_CSS_VAR_BY_TOKEN[key]] = tokens[key]
  }
  return out
}
