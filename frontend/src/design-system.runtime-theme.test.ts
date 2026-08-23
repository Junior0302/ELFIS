/**
 * @vitest-environment jsdom
 *
 * EX1 — Runtime product resolution & theme stability.
 */
import { describe, expect, it } from 'vitest'
import { resolveRuntimeProductFromPath } from './design-system/themes/resolveRuntimeProductFromPath'
import { createThemeEngine } from './design-system/themes/createThemeEngine'
import { PRODUCT_THEME_STORAGE_KEY } from './design-system/themes/persistence'
import { applyProductTheme, clearProductTheme } from './design-system/themes/applyProductTheme'
import { resolveProductTheme } from './design-system/themes/resolveProductTheme'

describe('resolveRuntimeProductFromPath', () => {
  it('/login → elfis-core', () => {
    expect(resolveRuntimeProductFromPath('/login').productId).toBe('elfis-core')
  })

  it('/ → elfis-core', () => {
    expect(resolveRuntimeProductFromPath('/').productId).toBe('elfis-core')
  })

  it('/home → elfis-core (platform)', () => {
    const r = resolveRuntimeProductFromPath('/home')
    expect(r.productId).toBe('elfis-core')
    expect(r.surface).toBe('platform')
    expect(r.persist).toBe(false)
  })

  it('/dashboard → comptapilot', () => {
    expect(resolveRuntimeProductFromPath('/dashboard').productId).toBe('comptapilot')
  })

  it('/platform/banking → elfis-core (sync hors Finance)', () => {
    expect(resolveRuntimeProductFromPath('/platform/banking').productId).toBe('elfis-core')
    expect(resolveRuntimeProductFromPath('/platform/banking').surface).toBe('platform')
  })

  it('/sales → salespilot', () => {
    expect(resolveRuntimeProductFromPath('/sales').productId).toBe('salespilot')
  })

  it('/sales/pipeline → salespilot', () => {
    expect(resolveRuntimeProductFromPath('/sales/pipeline').productId).toBe('salespilot')
  })

  it('sandbox ne persiste pas', () => {
    const r = resolveRuntimeProductFromPath('/dev/design-system/themes')
    expect(r.persist).toBe(false)
    expect(r.surface).toBe('sandbox')
  })

  it('pages publiques ne persiste pas', () => {
    expect(resolveRuntimeProductFromPath('/login').persist).toBe(false)
  })
})

describe('theme engine stability', () => {
  it('setCurrentProduct no-op ne change pas l’id', () => {
    const engine = createThemeEngine({
      initialProductId: 'comptapilot',
      persist: false,
      applyToDom: false,
      resolveFromPath: false,
    })
    expect(engine.setCurrentProduct('comptapilot')).toBe(true)
    expect(engine.getState().currentProductId).toBe('comptapilot')
    engine.destroy()
  })

  it('storage comptapilot n’écrase pas une résolution sales (route)', () => {
    try {
      localStorage.setItem(PRODUCT_THEME_STORAGE_KEY, 'comptapilot')
    } catch {
      /* ignore */
    }
    const pathRes = resolveRuntimeProductFromPath('/sales')
    expect(pathRes.productId).toBe('salespilot')
  })

  it('storage salespilot n’écrase pas /dashboard', () => {
    try {
      localStorage.setItem(PRODUCT_THEME_STORAGE_KEY, 'salespilot')
    } catch {
      /* ignore */
    }
    expect(resolveRuntimeProductFromPath('/dashboard').productId).toBe('comptapilot')
  })

  it('destroy ne clear pas le DOM (anti StrictMode flicker)', () => {
    const el = document.createElement('div')
    const theme = resolveProductTheme('salespilot')
    applyProductTheme(theme, el)
    expect(el.style.getPropertyValue('--pilot-primary')).toBeTruthy()
    const engine = createThemeEngine({
      initialProductId: 'salespilot',
      persist: false,
      applyToDom: true,
      target: el,
      resolveFromPath: false,
    })
    engine.destroy()
    // Tokens remain — no flash to empty/:root
    expect(el.style.getPropertyValue('--pilot-primary')).toBeTruthy()
    clearProductTheme(el)
  })

  it('applyProductTheme est atomique (pas de clear préalable)', () => {
    const el = document.createElement('div')
    applyProductTheme(resolveProductTheme('comptapilot'), el)
    const green = el.style.getPropertyValue('--pilot-primary')
    applyProductTheme(resolveProductTheme('salespilot'), el)
    const blue = el.style.getPropertyValue('--pilot-primary')
    expect(green).not.toBe(blue)
    expect(blue.toLowerCase()).toContain('1d4ed8')
    clearProductTheme(el)
  })

  it('elfis-core est activable même hors launcher business', () => {
    const engine = createThemeEngine({
      initialProductId: 'comptapilot',
      persist: false,
      applyToDom: false,
      resolveFromPath: false,
    })
    expect(engine.setCurrentProduct('elfis-core')).toBe(true)
    expect(engine.getState().currentProductId).toBe('elfis-core')
    engine.destroy()
  })
})
