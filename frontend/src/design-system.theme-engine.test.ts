import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import {
  PRODUCT_THEME_HOOK_ERROR,
  PRODUCT_THEME_STORAGE_KEY,
  PILOT_CSS_VAR_NAMES,
  PILOT_CSS_VAR_BY_TOKEN,
  PILOT_TOKEN_KEYS,
  applyProductTheme,
  assertProductThemeContext,
  buildLegacyPilotTokenMap,
  buildPilotTokens,
  clearPersistedProductId,
  clearProductTheme,
  createThemeEngine,
  getThemeBrandingAsset,
  isDesignSystemSandboxEnabled,
  readPersistedProductId,
  resolveProductTheme,
  themeToCssVariables,
  themeToDomAttributes,
  validateProductTheme,
  writePersistedProductId,
  PRODUCT_THEME_CHANGED_EVENT,
} from './design-system'
import type { ProductTheme } from './design-system'

function fakeTarget() {
  const props = new Map<string, string>()
  const attrs = new Map<string, string>()
  return {
    style: {
      setProperty: (k: string, v: string) => {
        props.set(k, v)
      },
      removeProperty: (k: string) => {
        props.delete(k)
      },
      getPropertyValue: (k: string) => props.get(k) ?? '',
    },
    setAttribute: (k: string, v: string) => {
      attrs.set(k, v)
    },
    removeAttribute: (k: string) => {
      attrs.delete(k)
    },
    _props: props,
    _attrs: attrs,
  }
}

describe('Theme Engine — resolve & tokens', () => {
  it('résout ComptaPilot', () => {
    const theme = resolveProductTheme('comptapilot')
    expect(theme.productId).toBe('comptapilot')
    expect(theme.themeId).toBe('comptapilot')
    expect(theme.colorScheme).toBe('light')
    expect(theme.tokens.primary.toLowerCase()).toBe('#0b3d2e')
  })

  it('résout SalesPilot', () => {
    const theme = resolveProductTheme('salespilot')
    expect(theme.productId).toBe('salespilot')
    expect(theme.branding.displayName).toBe('SalesPilot')
    expect(theme.tokens.primary).toMatch(/^#/)
  })

  it('résout DocPilot', () => {
    const theme = resolveProductTheme('docpilot')
    expect(theme.productId).toBe('docpilot')
    expect(theme.metadata.category).toBe('documents')
  })

  it('fallback sur ID inconnu (workspace → comptapilot)', () => {
    const theme = resolveProductTheme('unknown-product')
    expect(theme.productId).toBe('comptapilot')
    expect(theme.metadata.resolvedFromFallback).toBe(true)
  })

  it('fallback plateforme → elfis-core', () => {
    const theme = resolveProductTheme('nope', { surface: 'platform' })
    expect(theme.productId).toBe('elfis-core')
  })

  it('aucun token manquant', () => {
    const theme = resolveProductTheme('hrpilot')
    for (const key of PILOT_TOKEN_KEYS) {
      expect(theme.tokens[key]).toBeTruthy()
    }
  })

  it('themeId cohérent', () => {
    expect(resolveProductTheme('legalpilot').themeId).toBe('legalpilot')
  })

  it('branding cohérent', () => {
    const theme = resolveProductTheme('inventorypilot')
    expect(theme.branding.logo).toContain('/branding/products/inventorypilot/')
    expect(getThemeBrandingAsset(theme, 'logoMark')).toContain('logo-mark.svg')
    expect(theme.branding.displayName).toBe('InventoryPilot')
  })

  it('chart palette complète', () => {
    const t = buildPilotTokens('marketingpilot')
    expect([t.chart1, t.chart2, t.chart3, t.chart4, t.chart5, t.chart6, t.chart7, t.chart8].every(Boolean)).toBe(
      true,
    )
  })
})

describe('Theme Engine — CSS mapper', () => {
  it('convertit en variables CSS', () => {
    const theme = resolveProductTheme('projectpilot')
    const vars = themeToCssVariables(theme)
    expect(vars['--pilot-primary']).toBe(theme.tokens.primary)
    expect(vars['--pilot-focus']).toBe(theme.tokens.focus)
    expect(vars['--pilot-chart-1']).toBe(theme.tokens.chart1)
  })

  it('centralise les noms CSS', () => {
    expect(PILOT_CSS_VAR_BY_TOKEN.primary).toBe('--pilot-primary')
    expect(PILOT_CSS_VAR_NAMES).toContain('--pilot-primary-hover')
    expect(new Set(PILOT_CSS_VAR_NAMES).size).toBe(PILOT_CSS_VAR_NAMES.length)
  })

  it('expose data attributes', () => {
    const attrs = themeToDomAttributes(resolveProductTheme('supportpilot'))
    expect(attrs['data-product']).toBe('supportpilot')
    expect(attrs['data-theme']).toBe('supportpilot-light')
    expect(attrs['data-color-scheme']).toBe('light')
  })
})

describe('Theme Engine — DOM applier', () => {
  it('injecte les variables', () => {
    const el = fakeTarget()
    const theme = resolveProductTheme('comptapilot')
    applyProductTheme(theme, el)
    expect(el._props.get('--pilot-primary')).toBe(theme.tokens.primary)
    expect(el._props.get('--pilot-focus')).toBeTruthy()
  })

  it('ajoute data-product', () => {
    const el = fakeTarget()
    applyProductTheme(resolveProductTheme('salespilot'), el)
    expect(el._attrs.get('data-product')).toBe('salespilot')
    expect(el._attrs.get('data-theme')).toBe('salespilot-light')
  })

  it('clearProductTheme retire uniquement les tokens Pilot', () => {
    const el = fakeTarget()
    el.style.setProperty('--forest', '#0b3d2e')
    el.style.setProperty('--pilot-primary', '#111')
    applyProductTheme(resolveProductTheme('docpilot'), el)
    clearProductTheme(el)
    expect(el._props.has('--pilot-primary')).toBe(false)
    expect(el._props.get('--forest')).toBe('#0b3d2e')
    expect(el._attrs.has('data-product')).toBe(false)
  })

  it('fonctionne sans document', () => {
    const cleanup = applyProductTheme(resolveProductTheme('comptapilot'), null)
    expect(typeof cleanup).toBe('function')
    cleanup()
    clearProductTheme(null)
  })
})

describe('Theme Engine — persistence', () => {
  const mem = new Map<string, string>()

  beforeEach(() => {
    mem.clear()
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => mem.get(k) ?? null,
      setItem: (k: string, v: string) => {
        mem.set(k, v)
      },
      removeItem: (k: string) => {
        mem.delete(k)
      },
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('persiste un ID valide', () => {
    writePersistedProductId('comptapilot')
    expect(mem.get(PRODUCT_THEME_STORAGE_KEY)).toBe('comptapilot')
    expect(readPersistedProductId()).toEqual({ ok: true, productId: 'comptapilot' })
  })

  it('ignore une valeur persistée invalide', () => {
    mem.set(PRODUCT_THEME_STORAGE_KEY, 'not-a-product')
    expect(readPersistedProductId().ok).toBe(false)
  })

  it('refuse coming_soon en lecture application', () => {
    mem.set(PRODUCT_THEME_STORAGE_KEY, 'docpilot')
    expect(readPersistedProductId({ requireAvailable: true })).toEqual({
      ok: false,
      reason: 'unavailable',
    })
  })
})

describe('Theme Engine — runtime controller', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('refuse coming_soon hors shells en mode application', () => {
    const engine = createThemeEngine({
      applyToDom: false,
      persist: false,
      resolveFromPath: false,
      initialProductId: 'comptapilot',
    })
    expect(engine.setCurrentProduct('docpilot')).toBe(false)
    expect(engine.getState().currentProductId).toBe('comptapilot')
    expect(engine.getState().error).toMatch(/non disponible/i)
    engine.destroy()
  })

  it('autorise salespilot pour le theming shell (route)', () => {
    const engine = createThemeEngine({
      applyToDom: false,
      persist: false,
      resolveFromPath: false,
      initialProductId: 'comptapilot',
    })
    expect(engine.setCurrentProduct('salespilot')).toBe(true)
    expect(engine.getState().currentProductId).toBe('salespilot')
    engine.destroy()
  })

  it('autorise coming_soon en preview', () => {
    const engine = createThemeEngine({
      applyToDom: false,
      persist: false,
      allowPreviewUnavailableProducts: true,
    })
    expect(engine.setCurrentProduct('salespilot')).toBe(true)
    expect(engine.getState().currentProductId).toBe('salespilot')
    engine.destroy()
  })

  it('reset vers ComptaPilot', () => {
    const engine = createThemeEngine({
      applyToDom: false,
      persist: false,
      allowPreviewUnavailableProducts: true,
      initialProductId: 'docpilot',
    })
    engine.resetProductTheme()
    expect(engine.getState().currentProductId).toBe('comptapilot')
    engine.destroy()
  })

  it('setCurrentProduct applique un nouveau thème', () => {
    const el = fakeTarget()
    const engine = createThemeEngine({
      applyToDom: true,
      persist: false,
      allowPreviewUnavailableProducts: true,
      target: el,
      initialProductId: 'comptapilot',
    })
    engine.setCurrentProduct('docpilot')
    expect(el._attrs.get('data-product')).toBe('docpilot')
    expect(el._props.get('--pilot-primary')).toBe(resolveProductTheme('docpilot').tokens.primary)
    engine.destroy()
  })

  it('évite la réapplication identique', () => {
    const el = fakeTarget()
    const engine = createThemeEngine({
      applyToDom: true,
      persist: false,
      target: el,
      initialProductId: 'comptapilot',
    })
    const first = el._props.get('--pilot-primary')
    el.style.setProperty('--pilot-primary', '#ffffff')
    expect(engine.setCurrentProduct('comptapilot')).toBe(true)
    expect(el._props.get('--pilot-primary')).toBe('#ffffff')
    expect(first).toBeTruthy()
    engine.destroy()
  })

  it('émet un événement frontend optionnel', () => {
    const handler = vi.fn()
    if (typeof window !== 'undefined') {
      window.addEventListener(PRODUCT_THEME_CHANGED_EVENT, handler)
    }
    const engine = createThemeEngine({
      applyToDom: false,
      persist: false,
      allowPreviewUnavailableProducts: true,
    })
    engine.setCurrentProduct('hrpilot')
    engine.destroy()
    if (typeof window !== 'undefined') {
      window.removeEventListener(PRODUCT_THEME_CHANGED_EVENT, handler)
    }
  })
})

describe('Theme Engine — validation & context helpers', () => {
  it('détecte un thème invalide', () => {
    const theme = resolveProductTheme('comptapilot')
    const broken = {
      ...theme,
      tokens: { ...theme.tokens, primary: '' },
    } as ProductTheme
    const result = validateProductTheme(broken)
    expect(result.ok).toBe(false)
    expect(result.issues.some((i) => i.code === 'empty_token')).toBe(true)
  })

  it('expose le contexte via assert / erreur hors provider', () => {
    expect(() => assertProductThemeContext(null)).toThrow(PRODUCT_THEME_HOOK_ERROR)
  })

  it('conserve le map legacy E1.1', () => {
    const legacy = buildLegacyPilotTokenMap('elfis-core')
    expect(legacy['pilot-primary']).toMatch(/^#/)
  })

  it('sandbox flag cohérent avec import.meta.env.DEV', () => {
    expect(isDesignSystemSandboxEnabled()).toBe(import.meta.env.DEV === true)
  })
})
