/**
 * Runtime validation of generated ProductTheme objects.
 */

import { PILOT_TOKEN_KEYS } from '../tokens/pilotTokens'
import { PILOT_CSS_VAR_BY_TOKEN, PILOT_CSS_VAR_NAMES } from './cssVariables'
import type { ProductTheme, ThemeValidationIssue, ThemeValidationResult } from './interfaces'

const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/

function isCssColorValue(value: string): boolean {
  const v = value.trim()
  if (!v) return false
  if (HEX_RE.test(v)) return true
  if (v.startsWith('rgb(') || v.startsWith('rgba(') || v.startsWith('hsl(')) return true
  return false
}

export function validateProductTheme(theme: ProductTheme): ThemeValidationResult {
  const issues: ThemeValidationIssue[] = []

  if (!theme.productId || !theme.themeId) {
    issues.push({ code: 'missing_ids', message: 'productId and themeId are required' })
  }
  if (theme.themeId !== theme.productId) {
    issues.push({
      code: 'theme_id_mismatch',
      message: `themeId (${theme.themeId}) must match productId (${theme.productId}) in V1`,
    })
  }
  if (theme.colorScheme !== 'light') {
    issues.push({
      code: 'color_scheme',
      message: 'V1 only supports light colorScheme',
    })
  }

  for (const key of PILOT_TOKEN_KEYS) {
    const value = theme.tokens?.[key]
    if (value == null || value === undefined) {
      issues.push({ code: 'missing_token', message: `Missing token: ${key}` })
      continue
    }
    if (typeof value !== 'string' || !value.trim()) {
      issues.push({ code: 'empty_token', message: `Empty token: ${key}` })
      continue
    }
    if (!isCssColorValue(value)) {
      issues.push({ code: 'invalid_color', message: `Invalid color for ${key}: ${value}` })
    }
  }

  const cssNames = new Set<string>(PILOT_CSS_VAR_NAMES)
  if (cssNames.size !== PILOT_CSS_VAR_NAMES.length) {
    issues.push({ code: 'css_name_conflict', message: 'Duplicate CSS variable names' })
  }
  for (const key of PILOT_TOKEN_KEYS) {
    if (!PILOT_CSS_VAR_BY_TOKEN[key]) {
      issues.push({ code: 'css_map_gap', message: `No CSS var mapped for ${key}` })
    }
  }

  const charts = [
    theme.tokens.chart1,
    theme.tokens.chart2,
    theme.tokens.chart3,
    theme.tokens.chart4,
    theme.tokens.chart5,
    theme.tokens.chart6,
    theme.tokens.chart7,
    theme.tokens.chart8,
  ]
  if (charts.some((c) => !c?.trim())) {
    issues.push({ code: 'incomplete_chart', message: 'Chart palette must have 8 values' })
  }

  const branding = theme.branding
  if (
    !branding?.logo?.trim() ||
    !branding?.logoMark?.trim() ||
    !branding?.favicon?.trim() ||
    !branding?.displayName?.trim() ||
    !branding?.shortName?.trim()
  ) {
    issues.push({ code: 'branding', message: 'Branding paths / names incomplete' })
  }

  if (!theme.tokens.primaryContrast?.trim()) {
    issues.push({ code: 'contrast', message: 'primaryContrast required' })
  }

  if (!theme.tokens.gradientStart || !theme.tokens.gradientEnd) {
    issues.push({ code: 'gradient', message: 'gradientStart/End required' })
  }

  return { ok: issues.length === 0, issues }
}
