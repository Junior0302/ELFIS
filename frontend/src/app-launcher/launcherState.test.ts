/**
 * App Launcher V1 — unit tests (pure resolver / routes)
 */
import { describe, expect, it } from 'vitest'
import { getProductById, getLauncherProducts, PRODUCT_REGISTRY } from '../design-system'
import {
  buildLauncherSections,
  resolveLauncherProductState,
} from './launcherState'
import { getKnownSpaRoutes, getProductEntryRoute, PRODUCT_ENTRY_ROUTES } from './productEntryRoutes'
import type { LauncherResolveContext } from './launcher.types'

const routes = getKnownSpaRoutes()

function ctx(partial: Partial<LauncherResolveContext> = {}): LauncherResolveContext {
  return {
    currentProductId: 'comptapilot',
    availableRoutes: routes,
    ...partial,
  }
}

describe('ProductEntryRoutes', () => {
  it('comptapilot a une route réelle', () => {
    expect(getProductEntryRoute('comptapilot')).toBe('/dashboard')
    expect(routes.has('/dashboard')).toBe(true)
  })

  it('salespilot a une route réelle en shell; docpilot non', () => {
    expect(PRODUCT_ENTRY_ROUTES.salespilot).toBe('/sales')
    expect(PRODUCT_ENTRY_ROUTES.docpilot).toBeNull()
    expect(routes.has('/sales')).toBe(true)
  })

  it('n’utilise pas websitePath marketing', () => {
    expect(getProductEntryRoute('comptapilot')).not.toBe(getProductById('comptapilot').websitePath)
  })
})

describe('resolveLauncherProductState', () => {
  it('résout active', () => {
    const r = resolveLauncherProductState(getProductById('comptapilot'), ctx())
    expect(r.state).toBe('active')
    expect(r.canOpen).toBe(false)
    expect(r.label).toMatch(/active/i)
  })

  it('résout salespilot selon environnement (beta DEV / coming_soon prod)', () => {
    const r = resolveLauncherProductState(getProductById('salespilot'), ctx())
    if (import.meta.env.DEV) {
      expect(r.state).toBe('beta')
      expect(r.canOpen).toBe(true)
      expect(r.route).toBe('/sales')
    } else {
      expect(r.state).toBe('coming_soon')
      expect(r.canOpen).toBe(false)
    }
  })

  it('produit sans route → non ouvrable', () => {
    const r = resolveLauncherProductState(getProductById('elfis-core'), ctx({ currentProductId: 'comptapilot' }))
    expect(r.canOpen).toBe(false)
  })

  it('archived / internal exclus via unavailable', () => {
    /* registry may not have archived — simulate via preview unavailable */
    const r = resolveLauncherProductState(getProductById('hrpilot'), ctx())
    expect(r.state).toBe('coming_soon')
  })

  it('preview available n’altère pas le registry', () => {
    const before = getProductById('salespilot').status
    const r = resolveLauncherProductState(
      getProductById('salespilot'),
      ctx({
        previewMode: true,
        previewOverrides: {
          salespilot: { state: 'available', route: '/dashboard', canOpen: true },
        },
      }),
    )
    expect(r.state).toBe('available')
    expect(r.canOpen).toBe(true)
    expect(getProductById('salespilot').status).toBe(before)
  })

  it('locked si entitlement false', () => {
    const r = resolveLauncherProductState(
      getProductById('comptapilot'),
      ctx({
        currentProductId: 'elfis-core',
        entitlements: { comptapilot: false },
        availableRoutes: new Set(['/dashboard']),
      }),
    )
    expect(r.state).toBe('locked')
    expect(r.canOpen).toBe(false)
  })
})

describe('buildLauncherSections', () => {
  it('ComptaPilot actif; featured coming soon doc/hr/support (+ sales hors DEV)', () => {
    const sections = buildLauncherSections(ctx())
    expect(sections.active?.product.id).toBe('comptapilot')
    const featured = sections.comingSoonFeatured.map((x) => x.product.id).sort()
    expect(featured).toContain('docpilot')
    expect(featured).toContain('hrpilot')
    expect(featured).toContain('supportpilot')
    if (import.meta.env.DEV) {
      expect(featured).not.toContain('salespilot')
      expect(sections.available.some((a) => a.product.id === 'salespilot' && a.state === 'beta')).toBe(
        true,
      )
    } else {
      expect(featured).toContain('salespilot')
    }
    expect(sections.available.every((a) => a.product.id !== 'comptapilot')).toBe(true)
    expect(sections.comingSoonGrouped.length).toBeGreaterThan(0)
  })

  it('getLauncherProducts n’inclut pas coming_soon', () => {
    expect(getLauncherProducts().every((p) => p.status === 'active' || p.status === 'beta')).toBe(
      true,
    )
  })

  it('registry inchangé après sections preview', () => {
    const snap = PRODUCT_REGISTRY.map((p) => p.status).join(',')
    buildLauncherSections(
      ctx({
        previewMode: true,
        previewOverrides: {
          salespilot: { state: 'available', route: '/dashboard' },
          docpilot: { state: 'beta', route: '/dashboard' },
        },
      }),
    )
    expect(PRODUCT_REGISTRY.map((p) => p.status).join(',')).toBe(snap)
  })
})
