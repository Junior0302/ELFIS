/**
 * Resource Library — unit tests RL (automates)
 * @vitest-environment node
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { catalogItemToResource, resourceKindToCatalogKind } from './adapters/catalogToResource'
import { resourceToSearchResult } from './adapters/resourceToSearchResult'
import { getResourceActions } from './actions'
import {
  DISABLED_FAVORITES,
  DISABLED_MOST_USED,
  DISABLED_RECENTS,
} from './contracts/libraryMeta'
import {
  getActiveResourceSource,
  inventoryPilotResourceSource,
  localLibrarySource,
  resolveResourceSource,
} from './sources/resolveResourceSource'

vi.mock('../api', () => ({
  api: {
    listCatalog: vi.fn(async () => ({
      items: [
        {
          id: 1,
          name: 'Abonnement Pro',
          kind: 'service',
          unit: 'mois',
          unit_price_ht: 49,
          vat_rate: 20,
          active: true,
          updated_at: '2026-01-02T00:00:00Z',
        },
        {
          id: 2,
          name: 'Clé USB',
          kind: 'produit',
          unit: 'u',
          unit_price_ht: 12,
          vat_rate: 20,
          active: false,
        },
        {
          id: 3,
          name: 'Audit',
          kind: 'service',
          unit: 'j',
          unit_price_ht: 800,
          vat_rate: 10,
          active: true,
        },
      ],
    })),
    createCatalogItem: vi.fn(async (payload: { name: string; kind?: string }) => ({
      id: 99,
      name: payload.name,
      kind: payload.kind ?? 'produit',
      unit: 'unité',
      unit_price_ht: 1,
      vat_rate: 20,
      active: true,
    })),
    updateCatalogItem: vi.fn(async (id: number, payload: Record<string, unknown>) => ({
      id,
      name: (payload.name as string) ?? 'x',
      kind: (payload.kind as string) ?? 'produit',
      unit: (payload.unit as string) ?? 'u',
      unit_price_ht: (payload.unit_price_ht as number) ?? 0,
      vat_rate: (payload.vat_rate as number) ?? 20,
      active: (payload.active as boolean) ?? true,
    })),
    deleteCatalogItem: vi.fn(async () => ({ ok: true })),
  },
}))

describe('RL model / adapters', () => {
  it('mappe CatalogItem → Resource', () => {
    const r = catalogItemToResource({
      id: 7,
      name: 'X',
      kind: 'service',
      unit: 'h',
      unit_price_ht: 100,
      vat_rate: 20,
      active: true,
    })
    expect(r.kind).toBe('service')
    expect(r.sourceId).toBe('local_library')
    expect(r.catalogItemId).toBe(7)
    expect(r.status).toBe('active')
  })

  it('resourceKindToCatalogKind', () => {
    expect(resourceKindToCatalogKind('product')).toBe('produit')
    expect(resourceKindToCatalogKind('service')).toBe('service')
  })

  it('Resource → SearchResult pour ProductPicker', () => {
    const r = catalogItemToResource({
      id: 3,
      name: 'Audit',
      kind: 'service',
      unit: 'j',
      unit_price_ht: 800,
      vat_rate: 10,
      active: true,
    })
    const s = resourceToSearchResult(r)
    expect(s.type).toBe('service')
    expect(s.metadata?.unit_price_ht).toBe(800)
    expect(s.source).toBe('billing_catalog')
  })
})

describe('RL ResourceSource resolve', () => {
  it('local disponible, inventory stub', () => {
    expect(localLibrarySource.available).toBe(true)
    expect(inventoryPilotResourceSource.available).toBe(false)
    expect(resolveResourceSource('inventory_pilot').id).toBe('local_library')
    expect(getActiveResourceSource().id).toBe('local_library')
  })

  it('capabilities honnêtes', () => {
    expect(localLibrarySource.capabilities.favorites).toBe(false)
    expect(localLibrarySource.capabilities.packs).toBe(false)
    expect(localLibrarySource.capabilities.history).toBe(false)
  })
})

describe('RL LocalLibrarySource list/filter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('filtre par q et kind', async () => {
    const res = await localLibrarySource.list({
      token: 't',
      q: 'clé',
      kinds: ['product'],
      page: 1,
      pageSize: 10,
    })
    expect(res.total).toBe(1)
    expect(res.items[0]?.name).toBe('Clé USB')
  })

  it('filtre TVA + tri prix', async () => {
    const res = await localLibrarySource.list({
      token: 't',
      vatRates: [10],
      sort: 'price_desc',
      activeOnly: false,
      page: 1,
      pageSize: 10,
    })
    expect(res.items.every((i) => i.vatRate === 10)).toBe(true)
  })

  it('pagination', async () => {
    const page1 = await localLibrarySource.list({
      token: 't',
      page: 1,
      pageSize: 2,
    })
    expect(page1.items).toHaveLength(2)
    expect(page1.hasMore).toBe(true)
    const page2 = await localLibrarySource.list({
      token: 't',
      page: 2,
      pageSize: 2,
    })
    expect(page2.items.length).toBeGreaterThanOrEqual(1)
  })

  it('refuse create pack', async () => {
    await expect(
      localLibrarySource.create!(
        { name: 'Pack', kind: 'pack', unitPriceHt: 1, vatRate: 20 },
        't',
      ),
    ).rejects.toThrow(/packs/i)
  })
})

describe('RL meta providers disabled', () => {
  it('favoris / récents / most used off', async () => {
    expect(DISABLED_FAVORITES.enabled).toBe(false)
    expect(DISABLED_RECENTS.enabled).toBe(false)
    expect(DISABLED_MOST_USED.enabled).toBe(false)
    expect(await DISABLED_FAVORITES.list()).toEqual([])
  })
})

describe('RL actions', () => {
  it('historique disabled, edit/duplicate available local', () => {
    const actions = getResourceActions(localLibrarySource)
    expect(actions.find((a) => a.id === 'history')?.available).toBe(false)
    expect(actions.find((a) => a.id === 'edit')?.available).toBe(true)
    expect(actions.find((a) => a.id === 'duplicate')?.available).toBe(true)
  })
})
