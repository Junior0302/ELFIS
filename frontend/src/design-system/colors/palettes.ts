/** Official Pilot / platform color palettes — centralized, not applied yet. */

import type { ChartPalette, ProductColors, ProductId } from '../types'

function chart(
  c1: string,
  c2: string,
  c3: string,
  c4: string,
  c5: string,
  c6: string,
  c7: string,
  c8: string,
): ChartPalette {
  return [c1, c2, c3, c4, c5, c6, c7, c8] as const
}

/**
 * Proposed brand colors (E1.1).
 * ComptaPilot keeps emerald alignment with current `:root --forest / --mint-soft`.
 */
export const PRODUCT_PALETTES: Record<ProductId, ProductColors> = {
  'elfis-core': {
    primaryColor: '#071629', // navy-950 — identité ELFIS (BRAND.ELFIS.2)
    secondaryColor: '#EAF1FF', // blue-100
    accentColor: '#2764E7', // blue-600 signature
    chartPalette: chart(
      '#071629',
      '#2764E7',
      '#102746',
      '#EAF1FF',
      '#0B1F3A',
      '#5B8DEF',
      '#8893A5',
      '#DDE4EE',
    ),
  },
  comptapilot: {
    primaryColor: '#0B3D2E', // vert émeraude (actuel produit)
    secondaryColor: '#E7F2EC',
    accentColor: '#7BC4A0',
    chartPalette: chart(
      '#0B3D2E',
      '#7BC4A0',
      '#C4782B',
      '#10241C',
      '#3D8B6E',
      '#E7F2EC',
      '#B42318',
      '#E6DFD0',
    ),
  },
  salespilot: {
    primaryColor: '#1D4ED8', // bleu professionnel
    secondaryColor: '#E8F0FE',
    accentColor: '#60A5FA',
    chartPalette: chart(
      '#1D4ED8',
      '#60A5FA',
      '#93C5FD',
      '#1E3A8A',
      '#3B82F6',
      '#BFDBFE',
      '#64748B',
      '#0F172A',
    ),
  },
  docpilot: {
    primaryColor: '#6D28D9', // violet
    secondaryColor: '#F3E8FF',
    accentColor: '#A78BFA',
    chartPalette: chart(
      '#6D28D9',
      '#A78BFA',
      '#C4B5FD',
      '#4C1D95',
      '#8B5CF6',
      '#EDE9FE',
      '#7C3AED',
      '#DDD6FE',
    ),
  },
  hrpilot: {
    primaryColor: '#C2410C', // orange
    secondaryColor: '#FFF7ED',
    accentColor: '#FB923C',
    chartPalette: chart(
      '#C2410C',
      '#FB923C',
      '#FDBA74',
      '#9A3412',
      '#EA580C',
      '#FFEDD5',
      '#F97316',
      '#FED7AA',
    ),
  },
  legalpilot: {
    primaryColor: '#7F1D1D', // bordeaux
    secondaryColor: '#FEF2F2',
    accentColor: '#B91C1C',
    chartPalette: chart(
      '#7F1D1D',
      '#B91C1C',
      '#DC2626',
      '#450A0A',
      '#991B1B',
      '#FEE2E2',
      '#EF4444',
      '#FECACA',
    ),
  },
  inventorypilot: {
    primaryColor: '#0E7490', // cyan
    secondaryColor: '#ECFEFF',
    accentColor: '#22D3EE',
    chartPalette: chart(
      '#0E7490',
      '#22D3EE',
      '#67E8F9',
      '#155E75',
      '#06B6D4',
      '#CFFAFE',
      '#0891B2',
      '#A5F3FC',
    ),
  },
  marketingpilot: {
    primaryColor: '#A16207', // jaune / or maîtrisé (lisible UI)
    secondaryColor: '#FEFCE8',
    accentColor: '#EAB308',
    chartPalette: chart(
      '#A16207',
      '#EAB308',
      '#FACC15',
      '#713F12',
      '#CA8A04',
      '#FEF9C3',
      '#FDE047',
      '#FEF08A',
    ),
  },
  projectpilot: {
    primaryColor: '#0F766E', // turquoise
    secondaryColor: '#F0FDFA',
    accentColor: '#2DD4BF',
    chartPalette: chart(
      '#0F766E',
      '#2DD4BF',
      '#5EEAD4',
      '#115E59',
      '#14B8A6',
      '#CCFBF1',
      '#0D9488',
      '#99F6E4',
    ),
  },
  supportpilot: {
    primaryColor: '#3730A3', // indigo
    secondaryColor: '#EEF2FF',
    accentColor: '#818CF8',
    chartPalette: chart(
      '#3730A3',
      '#818CF8',
      '#A5B4FC',
      '#312E81',
      '#6366F1',
      '#E0E7FF',
      '#4F46E5',
      '#C7D2FE',
    ),
  },
}

/** Semantic aliases for future CSS custom properties (not wired to :root yet). */
export const LEGACY_COMPTAPILOT_CSS_VARS = {
  ink: '--ink',
  forest: '--forest',
  forestDeep: '--forest-deep',
  mint: '--mint',
  mintSoft: '--mint-soft',
  sand: '--sand',
  sandDeep: '--sand-deep',
  amber: '--amber',
  danger: '--danger',
  white: '--white',
  line: '--line',
} as const
