import { describe, expect, it } from 'vitest'
import {
  buildResultGroups,
  filterCommands,
  filterQuickActions,
  groupIdForResourceType,
  parseCommandMode,
  searchHitToItem,
  searchPageHref,
} from './commandModel'
import type { SearchEngineHit } from './commandTypes'

describe('parseCommandMode', () => {
  it('détecte le préfixe >', () => {
    expect(parseCommandMode('> nouvelle facture')).toEqual({
      active: true,
      commandText: 'nouvelle facture',
    })
    expect(parseCommandMode('facture')).toEqual({ active: false, commandText: '' })
  })
})

describe('filterQuickActions', () => {
  it('mappe facture → routes existantes', () => {
    const items = filterQuickActions('facture')
    const titles = items.map((i) => i.title)
    expect(titles).toContain('Nouvelle facture')
    expect(titles).toContain('Factures')
    expect(titles).toContain('Importer une facture')
    expect(items.every((i) => ['/facturation', '/deposit'].includes(i.href))).toBe(true)
  })

  it('mappe client → /clients', () => {
    const items = filterQuickActions('client')
    expect(items.some((i) => i.href === '/clients')).toBe(true)
  })

  it('mappe sales → SalesPilot', () => {
    const items = filterQuickActions('sales')
    expect(items.some((i) => i.href === '/sales' && i.title.includes('SalesPilot'))).toBe(true)
  })
})

describe('filterCommands', () => {
  it('liste les commandes V1 navigables', () => {
    const all = filterCommands('')
    expect(all.map((c) => c.href).sort()).toEqual(
      ['/dashboard', '/deposit', '/facturation', '/sales'].sort(),
    )
  })

  it('filtre ouvrir salespilot', () => {
    const items = filterCommands('ouvrir salespilot')
    expect(items.some((i) => i.href === '/sales')).toBe(true)
  })
})

describe('Search Engine grouping', () => {
  it('mappe resource_type vers sections', () => {
    expect(groupIdForResourceType('customer')).toBe('clients')
    expect(groupIdForResourceType('vault_document')).toBe('documents')
    expect(groupIdForResourceType('accounting_entry')).toBe('factures')
  })

  it('convertit un hit en item navigable', () => {
    const hit: SearchEngineHit = {
      search_document_id: 'sd1',
      resource_type: 'customer',
      resource_id: '42',
      title: 'Acme',
      snippet: 'Client',
      action_url: '/clients',
      score: 1,
    }
    const item = searchHitToItem(hit)
    expect(item?.group).toBe('clients')
    expect(item?.href).toBe('/clients')
  })
})

describe('buildResultGroups', () => {
  it('idle : applications + navigation', () => {
    const groups = buildResultGroups({
      query: '',
      commandMode: { active: false, commandText: '' },
      searchHits: [],
    })
    expect(groups.map((g) => g.id)).toEqual(['applications', 'navigation'])
    expect(groups.flatMap((g) => g.items).some((i) => i.href === '/dashboard')).toBe(true)
    expect(groups.flatMap((g) => g.items).some((i) => i.href === '/home')).toBe(true)
  })

  it('mode commande ignore les hits search', () => {
    const groups = buildResultGroups({
      query: '> ouvrir',
      commandMode: { active: true, commandText: 'ouvrir' },
      searchHits: [
        {
          search_document_id: 'x',
          resource_type: 'customer',
          resource_id: '1',
          title: 'X',
          snippet: '',
          score: 1,
        },
      ],
    })
    expect(groups.every((g) => g.id === 'commands')).toBe(true)
  })
})

describe('searchPageHref', () => {
  it('encode la query', () => {
    expect(searchPageHref('acme sas')).toBe('/search?q=acme%20sas')
  })
})
