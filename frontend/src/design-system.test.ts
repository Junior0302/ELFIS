import { describe, expect, it } from 'vitest'
import {
  DEFAULT_RUNTIME_PRODUCT_ID,
  PRODUCT_REGISTRY,
  PRODUCT_CATEGORIES,
  PRODUCT_ACCENT_GRADIENTS,
  buildPilotTokens,
  getProduct,
  getProductById,
  getProductBySlug,
  getProductsByCategory,
  getLauncherProducts,
  getActiveProducts,
  getComingSoonProducts,
  getStandaloneProducts,
  getBundleEligibleProducts,
  getProductCategory,
  isProductAvailable,
  isKnownProductId,
  listActiveProducts,
  listProducts,
  validateProductRegistry,
  PILOT_CSS_VAR_NAMES,
} from './design-system'

describe('ELFIS Design System Brand Foundation V1', () => {
  it('déclare tous les produits attendus', () => {
    const ids = PRODUCT_REGISTRY.map((p) => p.id)
    expect(ids).toEqual([
      'elfis-core',
      'comptapilot',
      'salespilot',
      'docpilot',
      'hrpilot',
      'legalpilot',
      'inventorypilot',
      'marketingpilot',
      'projectpilot',
      'supportpilot',
    ])
  })

  it('marque ELFIS Core et ComptaPilot comme active', () => {
    const active = listActiveProducts().map((p) => p.id)
    expect(active).toContain('elfis-core')
    expect(active).toContain('comptapilot')
    /* SalesPilot = beta en DEV → 7 coming_soon ; 8 en prod */
    expect(listProducts('coming_soon').length).toBeGreaterThanOrEqual(import.meta.env.DEV ? 7 : 8)
  })

  it('centralise les couleurs ComptaPilot alignées legacy', () => {
    const compta = getProduct('comptapilot')
    expect(compta.colors.primaryColor.toLowerCase()).toBe('#0b3d2e')
    expect(compta.colors.secondaryColor.toLowerCase()).toBe('#e7f2ec')
  })

  it('construit les tokens pilot-* sans les appliquer', () => {
    const tokens = buildPilotTokens('elfis-core')
    expect(tokens.primary).toMatch(/^#/)
    expect(tokens.chart1).toBeTruthy()
    expect(PILOT_CSS_VAR_NAMES).toContain('--pilot-primary')
  })

  it('expose le runtime produit actuel', () => {
    expect(DEFAULT_RUNTIME_PRODUCT_ID).toBe('comptapilot')
    expect(isKnownProductId('salespilot')).toBe(true)
    expect(isKnownProductId('unknown')).toBe(false)
  })

  it('prépare les chemins branding placeholders', () => {
    const branding = getProduct('docpilot').branding
    expect(branding.logo).toBe('/branding/products/docpilot/logo.svg')
    expect(branding.logoMark).toBe('/branding/products/docpilot/logo-mark.svg')
    expect(branding.favicon).toContain('favicon.svg')
  })
})

describe('E1.1.1 Product Identity & Categories', () => {
  it('garantit des IDs uniques', () => {
    const ids = PRODUCT_REGISTRY.map((p) => p.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('garantit des slugs uniques', () => {
    const slugs = PRODUCT_REGISTRY.map((p) => p.slug)
    expect(new Set(slugs).size).toBe(slugs.length)
  })

  it('référence des catégories valides', () => {
    const known = new Set(PRODUCT_CATEGORIES.map((c) => c.id))
    for (const product of PRODUCT_REGISTRY) {
      expect(known.has(product.category)).toBe(true)
    }
  })

  it('référence des themeId existants', () => {
    for (const product of PRODUCT_REGISTRY) {
      expect(product.themeId).toBe(product.id)
      expect(getProductById(product.themeId).colors.primaryColor).toMatch(/^#/)
    }
  })

  it('classe ELFIS Core comme platform', () => {
    expect(getProductById('elfis-core').productFamily).toBe('platform')
    expect(getProductById('elfis-core').category).toBe('platform')
  })

  it('classe les Pilots comme pilot_app', () => {
    for (const product of PRODUCT_REGISTRY) {
      if (product.id === 'elfis-core') continue
      expect(product.productFamily).toBe('pilot_app')
    }
  })

  it('mappe ComptaPilot → finance', () => {
    expect(getProductById('comptapilot').category).toBe('finance')
    expect(getProductCategory('comptapilot').id).toBe('finance')
  })

  it('mappe SalesPilot → sales', () => {
    expect(getProductById('salespilot').category).toBe('sales')
  })

  it('mappe DocPilot → documents', () => {
    expect(getProductById('docpilot').category).toBe('documents')
  })

  it('résout getProductById', () => {
    expect(getProductById('comptapilot').displayName).toBe('ComptaPilot')
  })

  it('résout getProductBySlug', () => {
    expect(getProductBySlug('salespilot')?.displayName).toBe('SalesPilot')
    expect(getProductBySlug('missing')).toBeUndefined()
  })

  it('filtre getProductsByCategory', () => {
    expect(getProductsByCategory('finance').map((p) => p.id)).toEqual(['comptapilot'])
    expect(getProductsByCategory('platform').map((p) => p.id)).toEqual(['elfis-core'])
  })

  it('exclut les produits non exposés du launcher', () => {
    const launcherIds = getLauncherProducts().map((p) => p.id)
    expect(launcherIds).toContain('elfis-core')
    expect(launcherIds).toContain('comptapilot')
    if (import.meta.env.DEV) {
      expect(launcherIds).toContain('salespilot')
    } else {
      expect(launcherIds).not.toContain('salespilot')
    }
    expect(launcherIds).not.toContain('docpilot')
  })

  it('liste les produits active', () => {
    expect(getActiveProducts().map((p) => p.id).sort()).toEqual(
      ['comptapilot', 'elfis-core'].sort(),
    )
  })

  it('liste les produits coming_soon', () => {
    const soon = getComingSoonProducts().map((p) => p.id)
    if (import.meta.env.DEV) {
      expect(soon).not.toContain('salespilot')
    } else {
      expect(soon).toContain('salespilot')
    }
    expect(soon).toContain('supportpilot')
    expect(soon).not.toContain('comptapilot')
  })

  it('liste les produits standalone éligibles (préparation commerciale)', () => {
    const standalone = getStandaloneProducts().map((p) => p.id)
    expect(standalone).toContain('comptapilot')
    expect(standalone).toContain('salespilot')
    expect(standalone).not.toContain('elfis-core')
  })

  it('liste les produits bundle-eligible', () => {
    const bundles = getBundleEligibleProducts().map((p) => p.id)
    expect(bundles).toContain('comptapilot')
    expect(bundles).toContain('docpilot')
    expect(bundles).not.toContain('elfis-core')
  })

  it('calcule isProductAvailable', () => {
    expect(isProductAvailable('comptapilot')).toBe(true)
    expect(isProductAvailable('elfis-core')).toBe(true)
  })

  it('refuse la disponibilité d’une app coming_soon', () => {
    if (import.meta.env.DEV) {
      expect(isProductAvailable('salespilot')).toBe(true)
    } else {
      expect(isProductAvailable('salespilot')).toBe(false)
    }
    expect(isProductAvailable('docpilot')).toBe(false)
  })

  it('refuse le standalone pour ELFIS Core', () => {
    const core = getProductById('elfis-core')
    expect(core.standaloneEligible).toBe(false)
    expect(core.pricingModel).toBe('included')
    expect(core.availableForSubscription).toBe(false)
  })

  it('définit les chemins branding', () => {
    const p = getProductById('hrpilot')
    expect(p.logo).toBe('/branding/products/hrpilot/logo.svg')
    expect(p.logoMark).toBe('/branding/products/hrpilot/logo-mark.svg')
    expect(p.favicon).toBe('/branding/products/hrpilot/favicon.svg')
    expect(p.branding.illustrations).toBe('/branding/products/hrpilot/illustrations/')
  })

  it('définit illustrationStyle pour chaque produit', () => {
    expect(getProductById('elfis-core').illustrationStyle).toBe('platform_minimal')
    expect(getProductById('comptapilot').illustrationStyle).toBe('financial_data')
    expect(getProductById('supportpilot').illustrationStyle).toBe('customer_support')
    for (const product of PRODUCT_REGISTRY) {
      expect(product.illustrationStyle).toBeTruthy()
    }
  })

  it('définit accentGradient pour chaque produit', () => {
    for (const product of PRODUCT_REGISTRY) {
      expect(product.accentGradient.from).toMatch(/^#/)
      expect(product.accentGradient.to).toMatch(/^#/)
      expect(PRODUCT_ACCENT_GRADIENTS[product.id]).toEqual(product.accentGradient)
    }
    expect(getProductById('comptapilot').accentGradient.from.toLowerCase()).toBe('#0b3d2e')
  })

  it('valide globalement le registry', () => {
    const result = validateProductRegistry()
    expect(result.issues).toEqual([])
    expect(result.ok).toBe(true)
  })

  it('expose des contenus produit cohérents', () => {
    const core = getProductById('elfis-core')
    expect(core.tagline).toContain('plateforme')
    expect(core.shortDescription.length).toBeGreaterThan(40)
    expect(getProductById('comptapilot').tagline).toContain('comptabilité')
  })
})
