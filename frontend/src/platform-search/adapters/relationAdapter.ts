/**
 * SharedRelation / Customer / Supplier → SearchResult.
 */

import type { CustomerRecord, SharedRelation } from '../../api'
import type { SearchResult } from '../types'

export function sharedRelationToSearchResult(
  r: SharedRelation,
  forcedType?: 'relation' | 'customer' | 'supplier',
): SearchResult {
  const isCustomer = r.roles.includes('customer') || r.source_system === 'customer'
  const isSupplier = r.roles.includes('supplier')
  let type: SearchResult['type'] = forcedType ?? 'relation'
  if (!forcedType) {
    if (isCustomer && !isSupplier) type = 'customer'
    else if (isSupplier && !isCustomer) type = 'supplier'
  }
  const email = r.emails[0] || ''
  const phone = r.phones[0]
  const address = r.addresses[0]
    ? [r.addresses[0].line1, r.addresses[0].city].filter(Boolean).join(', ')
    : undefined

  return {
    type,
    id: r.id,
    title: r.display_name || r.legal_name || 'Relation',
    subtitle: email || phone || undefined,
    description: address,
    status: r.status,
    route: `/platform/relations/${encodeURIComponent(r.id)}`,
    source: 'shared_relations',
    metadata: {
      relationId: r.id,
      source_system: r.source_system,
      source_entity_id: r.source_entity_id,
      roles: r.roles,
      email,
      phone,
      address,
      party_type: r.party_type,
    },
    actions: [
      { id: 'select', label: 'Sélectionner', kind: 'select' },
      {
        id: 'open_relations',
        label: 'Ouvrir Relations',
        kind: 'navigate',
        href: `/platform/relations/${encodeURIComponent(r.id)}`,
      },
    ],
  }
}

export function customerRecordToSearchResult(c: CustomerRecord): SearchResult {
  return {
    type: 'customer',
    id: `billing_customer:${c.id}`,
    title: c.name,
    subtitle: c.email || undefined,
    description: [c.phone, c.address].filter(Boolean).join(' · ') || undefined,
    route: '/clients',
    source: 'billing_customers',
    metadata: {
      customerId: c.id,
      relationId: null,
      email: c.email || '',
      phone: c.phone,
      address: c.address,
      billing_fallback: true,
    },
    actions: [{ id: 'select', label: 'Sélectionner', kind: 'select' }],
  }
}
