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
  achats: '#F59E0B',
  stock: '#EC4899',
  logistique: '#14B8A6',
  hr: '#F97316',
  planning: '#06B6D4',
  projets: '#EF4444',
  banque: '#059669',
  comptabilite: '#6366F1',
  facturation: '#EAB308',
  conformite: '#3B82F6',
  rse: '#22C55E',
  parametres: '#6B7280',
} as const

/** Variantes sombres (hover / contraste) — alignées WORKSPACE_ACCENTS.*.dark */
export const DEPARTMENT_ACCENT_DARK = {
  finance: '#15803D',
  commercial: '#1D4ED8',
  documents: '#6D28D9',
  achats: '#D97706',
  stock: '#DB2777',
  logistique: '#0D9488',
  hr: '#EA580C',
  planning: '#0891B2',
  projets: '#DC2626',
  banque: '#047857',
  comptabilite: '#4F46E5',
  facturation: '#CA8A04',
  conformite: '#2563EB',
  rse: '#16A34A',
  parametres: '#4B5563',
} as const
