/**
 * Accent gradients per product — derived from official palettes.
 * Not applied to CSS runtime in E1.1.1.
 */

import { PRODUCT_PALETTES } from './palettes'
import type { AccentGradient, ProductId } from '../types'

/**
 * from → to pairs for marketing / future theme accents.
 * Values stay hex strings centralized here.
 */
export const PRODUCT_ACCENT_GRADIENTS: Record<ProductId, AccentGradient> = {
  'elfis-core': {
    from: PRODUCT_PALETTES['elfis-core'].primaryColor,
    to: PRODUCT_PALETTES['elfis-core'].accentColor,
  },
  comptapilot: {
    from: PRODUCT_PALETTES.comptapilot.primaryColor, // émeraude
    to: PRODUCT_PALETTES.comptapilot.accentColor, // mint
  },
  salespilot: {
    from: PRODUCT_PALETTES.salespilot.primaryColor, // blue
    to: '#22D3EE', // cyan
  },
  docpilot: {
    from: PRODUCT_PALETTES.docpilot.primaryColor, // violet
    to: '#6366F1', // indigo
  },
  hrpilot: {
    from: PRODUCT_PALETTES.hrpilot.primaryColor, // orange
    to: '#C4782B', // amber
  },
  legalpilot: {
    from: PRODUCT_PALETTES.legalpilot.primaryColor, // burgundy
    to: '#9F1239', // rose sombre
  },
  inventorypilot: {
    from: PRODUCT_PALETTES.inventorypilot.primaryColor,
    to: PRODUCT_PALETTES.inventorypilot.accentColor,
  },
  marketingpilot: {
    from: PRODUCT_PALETTES.marketingpilot.primaryColor,
    to: PRODUCT_PALETTES.marketingpilot.accentColor,
  },
  projectpilot: {
    from: PRODUCT_PALETTES.projectpilot.primaryColor,
    to: PRODUCT_PALETTES.projectpilot.accentColor,
  },
  supportpilot: {
    from: PRODUCT_PALETTES.supportpilot.primaryColor,
    to: PRODUCT_PALETTES.supportpilot.accentColor,
  },
}

/** CSS linear-gradient string helper — unused by runtime until theming. */
export function accentGradientCss(gradient: AccentGradient, angleDeg = 135): string {
  return `linear-gradient(${angleDeg}deg, ${gradient.from} 0%, ${gradient.to} 100%)`
}

export function getAccentGradient(productId: ProductId): AccentGradient {
  return PRODUCT_ACCENT_GRADIENTS[productId]
}
