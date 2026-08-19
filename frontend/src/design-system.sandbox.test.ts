import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  DESIGN_SYSTEM_THEME_SANDBOX_PATH,
  PRODUCT_REGISTRY,
  createThemeEngine,
  isDesignSystemSandboxEnabled,
  resolveProductTheme,
} from './design-system'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('Theme Sandbox E1.2', () => {
  it('expose le chemin sandbox', () => {
    expect(DESIGN_SYSTEM_THEME_SANDBOX_PATH).toBe('/dev/design-system/themes')
  })

  it('n’apparaît pas dans la navigation métier', () => {
    const nav = readFileSync(join(root, 'src/navConfig.ts'), 'utf8')
    const navModel = readFileSync(join(root, 'src/navModel.ts'), 'utf8')
    expect(nav).not.toContain('design-system/themes')
    expect(navModel).not.toContain('design-system/themes')
  })

  it('route conditionnée DEV dans App.tsx', () => {
    const app = readFileSync(join(root, 'src/App.tsx'), 'utf8')
    expect(app).toContain('isDesignSystemSandboxEnabled')
    expect(app).toContain('dev/design-system/themes')
    expect(app).toContain('ThemeSandboxPage')
  })

  it('en production le helper désactive la sandbox', () => {
    // Vitest tourne en DEV ; on vérifie la sémantique du helper.
    expect(typeof isDesignSystemSandboxEnabled()).toBe('boolean')
    expect(isDesignSystemSandboxEnabled()).toBe(import.meta.env.DEV)
  })

  it('le sélecteur peut lister tous les produits en preview', () => {
    const engine = createThemeEngine({
      allowPreviewUnavailableProducts: true,
      applyToDom: false,
      persist: false,
    })
    expect(engine.availableProducts().map((p) => p.id)).toEqual(
      PRODUCT_REGISTRY.map((p) => p.id),
    )
    engine.destroy()
  })

  it('sélection SalesPilot change les tokens', () => {
    const engine = createThemeEngine({
      allowPreviewUnavailableProducts: true,
      applyToDom: false,
      persist: false,
    })
    const before = engine.getState().currentTheme.tokens.primary
    engine.setCurrentProduct('salespilot')
    expect(engine.getState().currentTheme.tokens.primary).not.toBe(before)
    expect(engine.getState().currentTheme.tokens.primary).toBe(
      resolveProductTheme('salespilot').tokens.primary,
    )
    engine.destroy()
  })

  it('sélection DocPilot change data-product via applier', () => {
    const props = new Map<string, string>()
    const attrs = new Map<string, string>()
    const el = {
      style: {
        setProperty: (k: string, v: string) => props.set(k, v),
        removeProperty: (k: string) => props.delete(k),
      },
      setAttribute: (k: string, v: string) => attrs.set(k, v),
      removeAttribute: (k: string) => attrs.delete(k),
    }
    const engine = createThemeEngine({
      allowPreviewUnavailableProducts: true,
      applyToDom: true,
      persist: false,
      target: el,
    })
    engine.setCurrentProduct('docpilot')
    expect(attrs.get('data-product')).toBe('docpilot')
    engine.destroy()
  })

  it('coming_soon prévisualisable', () => {
    const engine = createThemeEngine({
      allowPreviewUnavailableProducts: true,
      applyToDom: false,
      persist: false,
    })
    expect(engine.setCurrentProduct('supportpilot')).toBe(true)
    engine.destroy()
  })

  it('CSS sandbox n’utilise que --pilot-* (pas de legacy métier)', () => {
    const css = readFileSync(
      join(root, 'src/design-system/sandbox/themeSandbox.css'),
      'utf8',
    )
    expect(css).toContain('--pilot-primary')
    expect(css).not.toContain('--forest')
    expect(css).not.toContain('--mint')
    expect(css).not.toContain('className="btn"')
  })

  it('sandbox n’importe aucun composant métier', () => {
    const page = readFileSync(
      join(root, 'src/design-system/sandbox/ThemeSandboxPage.tsx'),
      'utf8',
    )
    expect(page).not.toMatch(/from ['"].*pages\//)
    expect(page).not.toMatch(/DashboardPage|WorkQueue|DecisionCard|Layout/)
    expect(page).toContain('htmlFor="ds-product-select"')
    expect(page).toContain('aria-live="polite"')
  })
})
