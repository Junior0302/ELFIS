/**
 * Contrat PilotTheme — accents uniquement (pas de layout/dimensions par Pilot).
 * Core navy / Compta vert / Sales bleu — via Theme Engine --pilot-* existant.
 */

import type { ProductId } from '../design-system'
import { PRODUCT_PALETTES } from '../design-system/colors/palettes'
import { getProductById } from '../design-system'

/** Pilots couverts Vague 1 (shell unifié). */
export type UnifiedPilotId = Extract<ProductId, 'elfis-core' | 'comptapilot' | 'salespilot'>

export type PilotAccentContract = {
  pilotId: UnifiedPilotId
  displayName: string
  shortName: string
  /** Couleur d’accent Pilot (CTA, active nav, focus). */
  accent: string
  /** Primaire Pilot (titres / active inset). */
  primary: string
  /** Surface douce Pilot. */
  secondary: string
  /** Classe shell pour accents CSS (pas de dimensions). */
  shellAccentClass: string
  /** Classe sidebar produit. */
  sidebarAccentClass: string
}

const ACCENT_CLASS: Record<UnifiedPilotId, { shell: string; sidebar: string }> = {
  'elfis-core': { shell: 'ps-shell--home', sidebar: 'ps-sidebar--home' },
  comptapilot: { shell: 'ps-shell--compta', sidebar: 'ps-sidebar--compta' },
  salespilot: { shell: 'ps-shell--sales', sidebar: 'ps-sidebar--sales' },
}

export function isUnifiedPilotId(id: string): id is UnifiedPilotId {
  return id === 'elfis-core' || id === 'comptapilot' || id === 'salespilot'
}

/**
 * Résout le contrat accent-only pour un Pilot.
 * Dimensions shell / topbar / sidebar = tokens plateforme, jamais ici.
 */
export function resolvePilotTheme(pilotId: ProductId): PilotAccentContract {
  const id: UnifiedPilotId = isUnifiedPilotId(pilotId) ? pilotId : 'elfis-core'
  const palette = PRODUCT_PALETTES[id]
  const product = getProductById(id)
  const classes = ACCENT_CLASS[id]
  return {
    pilotId: id,
    displayName: product.displayName,
    shortName: product.shortName,
    accent: palette.accentColor,
    primary: palette.primaryColor,
    secondary: palette.secondaryColor,
    shellAccentClass: classes.shell,
    sidebarAccentClass: classes.sidebar,
  }
}

/** Accents attendus Vague 1 (tests / doc). */
export const PILOT_ACCENT_EXPECTATIONS: Record<
  UnifiedPilotId,
  { primary: string; accent: string }
> = {
  'elfis-core': { primary: '#071629', accent: '#2764E7' },
  comptapilot: { primary: '#0B3D2E', accent: '#7BC4A0' },
  salespilot: { primary: '#1D4ED8', accent: '#60A5FA' },
}
