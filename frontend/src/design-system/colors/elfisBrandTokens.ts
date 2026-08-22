/**
 * Tokens couleur officiels ELFIS (BRAND.ELFIS.2).
 * Source unique — les surfaces plateforme aliasent vers --elfis-* / --pilot-*.
 * Ne pas dupliquer ailleurs avec des hex métier (Finance/Commercial/…).
 */

export const ELFIS_BRAND_COLORS = {
  navy950: '#071629',
  navy900: '#102746',
  /** Signature navy historique (launcher / gnav) — entre 950 et 900. */
  navySignature: '#0B1F3A',
  blue600: '#2764E7',
  blue100: '#EAF1FF',
  page: '#F5F7FA',
  surface: '#FFFFFF',
  surfaceMuted: '#F8FAFC',
  border: '#DDE4EE',
  textPrimary: '#101828',
  textSecondary: '#58657A',
  textMuted: '#8893A5',
  success: '#16845B',
  warning: '#C97816',
  danger: '#C83F49',
  info: '#2764E7',
} as const

export type ElfisBrandColorKey = keyof typeof ELFIS_BRAND_COLORS

/** Noms CSS custom properties --elfis-*. */
export const ELFIS_BRAND_CSS_VARS = {
  navy950: '--elfis-navy-950',
  navy900: '--elfis-navy-900',
  navySignature: '--elfis-navy-signature',
  blue600: '--elfis-blue-600',
  blue100: '--elfis-blue-100',
  page: '--elfis-page',
  surface: '--elfis-surface',
  surfaceMuted: '--elfis-surface-muted',
  border: '--elfis-border',
  textPrimary: '--elfis-text-primary',
  textSecondary: '--elfis-text-secondary',
  textMuted: '--elfis-text-muted',
  success: '--elfis-success',
  warning: '--elfis-warning',
  danger: '--elfis-danger',
  info: '--elfis-info',
} as const

/** Accents métier — primaires officiels workspace (voir src/workspaces/accents.ts). */
export const DEPARTMENT_ACCENTS = {
  finance: '#16A34A',
  commercial: '#2563EB',
  documents: '#7C3AED',
  hr: '#C2410C',
  analyse: '#0E7490',
  support: '#3730A3',
} as const

/** Variantes sombres (hover / contraste) — alignées WORKSPACE_ACCENTS.*.dark */
export const DEPARTMENT_ACCENT_DARK = {
  finance: '#0B3D2E',
  commercial: '#1D4ED8',
  documents: '#6D28D9',
  hr: '#9A3412',
  analyse: '#155E75',
  support: '#312E81',
} as const
