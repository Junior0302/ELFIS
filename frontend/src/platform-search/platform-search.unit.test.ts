/**
 * Platform Search — unit tests PSS01–PSS12, PSS19–PSS20
 * @vitest-environment node
 */
import { describe, expect, it } from 'vitest'
import { engineHitToSearchResult } from './adapters/searchEngineAdapter'
import {
  customerRecordToSearchResult,
  sharedRelationToSearchResult,
} from './adapters/relationAdapter'
import { catalogItemToSearchResult, salesDocToSearchResult } from './adapters/documentAdapter'
import { groupResultsByType, mapEngineResourceType } from './mapResourceType'
import { handleListKeyboard, GLOBAL_SHORTCUT_OWNER } from './keyboard'
import {
  inventoryPilotProductSource,
  localCatalogProductSource,
} from './sources/productSource'
import { DISABLED_FAVORITES, DISABLED_RECENTS } from './sources/smartSearchSources'
import { searchResultToCustomerSelection } from './pickers/CustomerPicker'
import { catalogResultToLineFields } from './pickers/ProductPicker'
import type { SharedRelation } from '../api'

const sampleRelation = (over: Partial<SharedRelation> = {}): SharedRelation => ({
  id: 'customer:12',
  organization_id: 1,
  party_type: 'organization',
  display_name: 'Acme',
  legal_name: 'Acme SAS',
  first_name: '',
  last_name: '',
  emails: ['a@acme.fr'],
  phones: ['0102030405'],
  addresses: [{ line1: '1 rue', line2: '', postal_code: '75001', city: 'Paris', country: 'FR' }],
  tax_number: '',
  siren: '',
  siret: '',
  roles: ['customer'],
  status: 'active',
  source_system: 'customer',
  source_entity_id: 12,
  ...over,
})

describe('PSS01 engine adapter', () => {
  it('mappe un hit Search Engine V1', () => {
    const r = engineHitToSearchResult({
      search_document_id: 'sd-1',
      resource_type: 'customer',
      resource_id: '9',
      title: 'Client Démo',
      subtitle: 'Paris',
      snippet: 'Snippet',
      action_url: '/clients',
      score: 2.5,
    })
    expect(r.source).toBe('search_engine_v1')
    expect(r.type).toBe('customer')
    expect(r.id).toBe('9')
    expect(r.route).toBe('/clients')
    expect(r.score).toBe(2.5)
  })
})

describe('PSS02 relation adapters', () => {
  it('SharedRelation → SearchResult opaque', () => {
    const r = sharedRelationToSearchResult(sampleRelation(), 'customer')
    expect(r.id).toBe('customer:12')
    expect(r.type).toBe('customer')
    expect(r.source).toBe('shared_relations')
  })

  it('CustomerRecord fallback', () => {
    const r = customerRecordToSearchResult({
      id: 5,
      name: 'Billing Co',
      email: 'b@co.fr',
      phone: '',
      address: '',
      vat_number: '',
    })
    expect(r.id).toBe('billing_customer:5')
    expect(r.metadata?.billing_fallback).toBe(true)
  })
})

describe('PSS03 document / catalog adapters', () => {
  it('SalesDoc types', () => {
    expect(salesDocToSearchResult({
      id: 1,
      doc_type: 'invoice',
      number: 'F-1',
      issue_date: '',
      due_date: '',
      status: 'draft',
      customer_name: 'X',
      customer_email: '',
      amount_ht: 10,
      amount_tva: 2,
      amount_ttc: 12,
      vat_rate: 20,
      paid_amount: 0,
      signature_status: '',
      notes: '',
    }).type).toBe('invoice')

    expect(salesDocToSearchResult({
      id: 2,
      doc_type: 'quote',
      number: 'D-1',
      issue_date: '',
      due_date: '',
      status: 'draft',
      customer_name: 'X',
      customer_email: '',
      amount_ht: 10,
      amount_tva: 2,
      amount_ttc: 12,
      vat_rate: 20,
      paid_amount: 0,
      signature_status: '',
      notes: '',
    }).type).toBe('quote')
  })

  it('catalog item', () => {
    const r = catalogItemToSearchResult({
      id: 3,
      name: 'Presta',
      kind: 'service',
      unit: 'h',
      unit_price_ht: 100,
      vat_rate: 20,
      active: true,
    })
    expect(r.type).toBe('service')
    expect(r.source).toBe('billing_catalog')
  })
})

describe('PSS04–PSS05 mapping / groups', () => {
  it('mapEngineResourceType', () => {
    expect(mapEngineResourceType('customer')).toBe('customer')
    expect(mapEngineResourceType('vault_document')).toBe('vault_document')
    expect(mapEngineResourceType('unknown_xyz')).toBe('unknown')
  })

  it('groupResultsByType', () => {
    const groups = groupResultsByType([
      { type: 'customer', id: '1', title: 'A', source: 'x' },
      { type: 'invoice', id: '2', title: 'B', source: 'x' },
      { type: 'customer', id: '3', title: 'C', source: 'x' },
    ])
    expect(groups).toHaveLength(2)
    expect(groups[0].items).toHaveLength(2)
  })
})

describe('PSS06 keyboard', () => {
  it('navigue et sélectionne', () => {
    let active = 0
    const selected: number[] = []
    const ev = (key: string) => {
      const e = { key, preventDefault: () => {} }
      handleListKeyboard(e, {
        itemCount: 3,
        activeIndex: active,
        setActiveIndex: (i) => {
          active = i
        },
        onSelect: (i) => selected.push(i),
        onEscape: () => selected.push(-1),
      })
    }
    ev('ArrowDown')
    expect(active).toBe(1)
    ev('ArrowUp')
    expect(active).toBe(0)
    ev('Enter')
    expect(selected).toContain(0)
    ev('Escape')
    expect(selected).toContain(-1)
  })
})

describe('PSS07 / PSS20 Command Center shortcut owner', () => {
  it('ne revendique pas Cmd+K', () => {
    expect(GLOBAL_SHORTCUT_OWNER).toBe('platform-command/CommandCenter')
  })
})

describe('PSS08–PSS09 ProductSource', () => {
  it('local disponible, inventory non', () => {
    expect(localCatalogProductSource.available).toBe(true)
    expect(inventoryPilotProductSource.available).toBe(false)
    expect(localCatalogProductSource.resourceSourceId).toBe('local_library')
    expect(inventoryPilotProductSource.resourceSourceId).toBe('inventory_pilot')
  })
})

describe('PSS10–PSS11 selection helpers', () => {
  it('opaque SharedRelation', () => {
    const raw = sharedRelationToSearchResult(sampleRelation(), 'customer')
    const sel = searchResultToCustomerSelection(raw)
    expect(sel.relationId).toBe('customer:12')
    expect(sel.customerId).toBe(12)
    expect(sel.source).toBe('shared_relation')
  })

  it('catalog line fields', () => {
    const fields = catalogResultToLineFields(
      catalogItemToSearchResult({
        id: 9,
        name: 'Article',
        kind: 'product',
        unit: 'u',
        unit_price_ht: 42,
        vat_rate: 5.5,
        active: true,
      }),
    )
    expect(fields.catalogItemId).toBe(9)
    expect(fields.unitPrice).toBe(42)
    expect(fields.vatRate).toBe(5.5)
  })
})

describe('PSS12 recents/favorites off', () => {
  it('désactivés sans source métier', async () => {
    expect(DISABLED_RECENTS.enabled).toBe(false)
    expect(DISABLED_FAVORITES.enabled).toBe(false)
    expect(await DISABLED_RECENTS.list()).toEqual([])
  })
})

describe('PSS19 pas de moteur FE', () => {
  it('adapters n’implémentent pas de fuzzy', () => {
    const src = engineHitToSearchResult.toString()
    expect(src).not.toMatch(/fuse|fuzzysort|levenshtein/i)
  })
})
