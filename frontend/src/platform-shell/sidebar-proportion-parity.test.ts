/**
 * @vitest-environment node
 * Parité proportions sidebar Home / Finance / Commercial — tokens --product-sidebar-*.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '../..')
const shellCss = readFileSync(resolve(root, 'src/platform-shell/platform-shell.css'), 'utf8')
const gnavCss = readFileSync(
  resolve(root, 'src/platform-shell/global-nav/elfis-global-navigation.css'),
  'utf8',
)
const indexCss = readFileSync(resolve(root, 'src/index.css'), 'utf8')
const homeCss = readFileSync(resolve(root, 'src/home/home.css'), 'utf8')
const upCss = readFileSync(resolve(root, 'src/unified-platform/unified-platform.css'), 'utf8')

const TOKEN_KEYS = [
  '--product-sidebar-expanded-width',
  '--product-sidebar-collapsed-width',
  '--product-sidebar-item-min-height',
  '--product-sidebar-item-pad-block',
  '--product-sidebar-item-pad-inline',
  '--product-sidebar-item-gap',
  '--product-sidebar-icon-size',
  '--product-sidebar-label-size',
  '--product-sidebar-section-gap',
  '--product-sidebar-section-title-size',
  '--product-sidebar-collapse-size',
  '--product-sidebar-toolbar-pad',
  '--product-sidebar-items-gap',
] as const

describe('sidebar proportion parity — SP.*', () => {
  it('SP01 — tokens définis sur .ps-shell', () => {
    for (const key of TOKEN_KEYS) {
      expect(shellCss).toContain(`${key}:`)
    }
    expect(shellCss).toMatch(/--product-sidebar-expanded-width:\s*240px/)
    expect(shellCss).toMatch(/--product-sidebar-collapsed-width:\s*56px/)
    expect(shellCss).toMatch(/--product-sidebar-item-min-height:\s*2\.55rem/)
    expect(shellCss).toMatch(/--product-sidebar-icon-size:\s*34px/)
    expect(shellCss).toMatch(/--product-sidebar-collapse-size:\s*32px/)
  })

  it('SP02 — Home elfis-gnav consomme les mêmes vars item', () => {
    expect(gnavCss).toMatch(
      /\.elfis-gnav__link\s*\{[\s\S]*min-height:\s*var\(--product-sidebar-item-min-height/s,
    )
    expect(gnavCss).toMatch(
      /\.elfis-gnav__link\s*\{[\s\S]*padding:\s*var\(--product-sidebar-item-pad-block/s,
    )
    expect(gnavCss).toMatch(
      /\.elfis-gnav__link\s*\{[\s\S]*gap:\s*var\(--product-sidebar-item-gap/s,
    )
    expect(gnavCss).toMatch(
      /\.elfis-gnav__link\s*\{[\s\S]*font-size:\s*var\(--product-sidebar-label-size/s,
    )
    expect(gnavCss).toMatch(
      /\.elfis-gnav__icon\s*\{[\s\S]*width:\s*var\(--product-sidebar-icon-size/s,
    )
    expect(gnavCss).toMatch(
      /\.elfis-gnav__heading\s*\{[\s\S]*font-size:\s*var\(--product-sidebar-section-title-size/s,
    )
    expect(gnavCss).toMatch(
      /\.elfis-gnav__toolbar\s*\{[\s\S]*padding:\s*var\(--product-sidebar-toolbar-pad/s,
    )
  })

  it('SP03 — Finance/Sales .nav-categories consomment les mêmes vars', () => {
    expect(indexCss).toMatch(
      /\.nav-category-btn\s*\{[\s\S]*min-height:\s*var\(--product-sidebar-item-min-height/s,
    )
    expect(indexCss).toMatch(
      /\.nav-categories\s+\.nav\s+a\s*\{[\s\S]*min-height:\s*var\(--product-sidebar-item-min-height/s,
    )
    expect(indexCss).toMatch(
      /\.nav-icon\s*\{[\s\S]*width:\s*var\(--product-sidebar-icon-size/s,
    )
    expect(indexCss).toMatch(
      /\.sidebar-collapse-btn\s*\{[\s\S]*width:\s*var\(--product-sidebar-collapse-size/s,
    )
  })

  it('SP04 — Home n’a plus de largeur 190px locale', () => {
    expect(homeCss).not.toMatch(/--ps-sidebar-w:\s*190px/)
    expect(homeCss).toMatch(
      /padding:\s*var\(--product-sidebar-surface-pad-block-start/s,
    )
  })

  it('SP05 — collapse Home aligne padding inline sur token', () => {
    expect(gnavCss).toMatch(
      /\.elfis-gnav\.is-collapsed\s+\.elfis-gnav__link\s*\{[\s\S]*padding-left:\s*var\(--product-sidebar-collapsed-item-pad-inline/s,
    )
  })

  it('SP06 — surfaces unifiées + toolbars Sales utilisent tokens', () => {
    expect(upCss).toMatch(/--product-sidebar-surface-pad-block-start/)
    expect(upCss).toMatch(
      /\.sales-product-nav__toolbar\s*\{[\s\S]*padding:\s*var\(--product-sidebar-toolbar-pad/s,
    )
  })
})
