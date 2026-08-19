import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { buildPilotTokens, resolveProductTheme } from './design-system'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('E1.3 Semantic Theme Migration', () => {
  it('aligne ComptaPilot sur les tokens legacy forest/mint/ink', () => {
    const t = buildPilotTokens('comptapilot')
    expect(t.primary.toLowerCase()).toBe('#0b3d2e')
    expect(t.primaryHover.toLowerCase()).toBe('#07281e')
    expect(t.primaryActive.toLowerCase()).toBe('#07281e')
    expect(t.secondary.toLowerCase()).toBe('#e7f2ec')
    expect(t.accent.toLowerCase()).toBe('#7bc4a0')
    expect(t.focus.toLowerCase()).toBe('#7bc4a0')
    expect(t.text.toLowerCase()).toBe('#10241c')
  })

  it('migre .btn vers --pilot-primary avec fallback legacy', () => {
    const css = readFileSync(join(root, 'src/index.css'), 'utf8')
    expect(css).toMatch(/\.btn\s*\{[^}]*--pilot-primary/s)
    expect(css).toContain('var(--pilot-primary, var(--forest))')
    expect(css).toContain('var(--pilot-primary-hover, var(--forest-deep))')
    expect(css).toContain('.btn:focus-visible')
  })

  it('migre nav active / badge accent / focus champs', () => {
    const css = readFileSync(join(root, 'src/index.css'), 'utf8')
    expect(css).toContain('.nav a.active')
    expect(css).toMatch(/\.nav a\.active\s*\{[^}]*--pilot-accent/s)
    expect(css).toMatch(/\.badge\s*\{[^}]*--pilot-secondary/s)
    expect(css).toContain('var(--pilot-focus, var(--mint))')
  })

  it('ne migre pas les badges métier ok/warn/danger vers pilot', () => {
    const css = readFileSync(join(root, 'src/index.css'), 'utf8')
    expect(css).toContain('.ui-badge--ok')
    expect(css).toContain('.ui-badge--warn')
    expect(css).toContain('.ui-badge--danger')
    expect(css).toMatch(/\.ui-badge--ok\s*\{[^}]*--mint/s)
    expect(css).toMatch(/\.ui-badge--danger\s*\{[^}]*--danger/s)
    expect(css).toMatch(/\.btn\.danger-outline\s*\{[^}]*--danger/s)
  })

  it('conserve les variables legacy :root', () => {
    const css = readFileSync(join(root, 'src/index.css'), 'utf8')
    expect(css).toContain('--forest: #0b3d2e')
    expect(css).toContain('--mint: #7bc4a0')
    expect(css).toContain('--ink: #10241c')
    expect(css).toContain('--pilot-primary: #0b3d2e')
  })

  it('SalesPilot / DocPilot restent distincts pour la sandbox', () => {
    const sales = resolveProductTheme('salespilot').tokens.primary
    const docs = resolveProductTheme('docpilot').tokens.primary
    const compta = resolveProductTheme('comptapilot').tokens.primary
    expect(sales).not.toBe(compta)
    expect(docs).not.toBe(compta)
    expect(sales).not.toBe(docs)
  })
})
