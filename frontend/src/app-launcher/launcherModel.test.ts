/**
 * launcherModel — pure unit tests
 * @vitest-environment jsdom
 */
import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import { getProductById } from '../design-system'
import {
  filterLauncherItems,
  getAvailableDisplayItems,
  getLauncherFooterLinks,
  matchesLauncherQuery,
  resolveContinueItem,
} from './launcherModel'
import type { LauncherResolveContext, LauncherSections, ResolvedLauncherProduct } from './launcher.types'

function resetStorage() {
  try {
    window.localStorage?.removeItem('elfis_last_product')
    window.localStorage?.removeItem('elfis_last_product_at')
  } catch {
    /* ignore */
  }
}

function item(
  id: 'comptapilot' | 'salespilot' | 'docpilot',
  state: ResolvedLauncherProduct['state'],
): ResolvedLauncherProduct {
  return {
    product: getProductById(id),
    state,
    canOpen: state === 'available' || state === 'active' || state === 'beta',
    label: '',
    route: id === 'comptapilot' ? '/dashboard' : id === 'salespilot' ? '/sales' : undefined,
  }
}

const sections: LauncherSections = {
  active: item('comptapilot', 'active'),
  available: [item('salespilot', 'available')],
  locked: [],
  comingSoonFeatured: [item('docpilot', 'coming_soon')],
  comingSoonGrouped: [],
}

const ctx: LauncherResolveContext = {
  currentProductId: 'comptapilot',
  availableRoutes: new Set(['/dashboard', '/sales']),
}

describe('launcherModel', () => {
  beforeEach(resetStorage)
  afterEach(resetStorage)

  it('footer : routes réelles uniquement', () => {
    const links = getLauncherFooterLinks()
    expect(links.map((l) => l.to)).toEqual([
      '/home',
      '/platform/organization',
      '/platform/documents',
      '/platform/relations',
      '/platform/communications',
      '/platform/settings',
    ])
    expect(links[0]?.label).toBe('Accueil ELFIS')
    expect(links.every((l) => !/aide|support|marketplace|découvrir/i.test(l.label))).toBe(true)
  })

  it('available display inclut active + available', () => {
    const list = getAvailableDisplayItems(sections)
    expect(list.map((i) => i.product.id)).toEqual(['comptapilot', 'salespilot'])
  })

  it('continue = lastProduct réel ; sinon fallback ComptaPilot', () => {
    const none = resolveContinueItem(sections, ctx, null)
    expect(none.continueItem).toBeNull()
    expect(none.fallbackContinue?.product.id).toBe('comptapilot')

    const withLast = resolveContinueItem(sections, ctx, 'salespilot')
    expect(withLast.continueItem?.product.id).toBe('salespilot')
    expect(withLast.continueItem?.isLastUsed).toBe(true)
    expect(withLast.fallbackContinue).toBeNull()
  })

  it('filtre nom / capacité / status', () => {
    const all = [...getAvailableDisplayItems(sections), ...sections.comingSoonFeatured]
    expect(filterLauncherItems(all, 'Facturation').map((i) => i.product.id)).toContain('comptapilot')
    expect(matchesLauncherQuery(item('docpilot', 'coming_soon'), 'bientôt')).toBe(true)
  })
})
