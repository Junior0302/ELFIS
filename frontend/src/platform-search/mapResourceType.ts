/**
 * Mapping resource_type Search Engine V1 → SearchEntityType Smart Search.
 * Ne invente pas de types absents de l’index.
 */

import type { SearchEntityType } from './types'

const ENGINE_TYPE_MAP: Record<string, SearchEntityType> = {
  customer: 'customer',
  supplier: 'supplier',
  vault_document: 'vault_document',
  document_text_extraction: 'document',
  document_analysis: 'document',
  accounting_proposal: 'document',
  accounting_entry: 'accounting_entry',
  sales_lead: 'relation',
  sales_company: 'relation',
  sales_person: 'relation',
  sales_opportunity: 'relation',
  sales_task: 'document',
  sales_activity: 'document',
  sales_proposal: 'quote',
}

/** Types V1 Smart Search qui ont une source réelle (index ou API domaine). */
export const V1_ENTITY_TYPES_WITH_SOURCE: readonly SearchEntityType[] = [
  'relation',
  'customer',
  'supplier',
  'document',
  'invoice',
  'quote',
  'credit_note',
  'product',
  'service',
  'accounting_entry',
  'vault_document',
] as const

export function mapEngineResourceType(resourceType: string): SearchEntityType {
  return ENGINE_TYPE_MAP[resourceType] ?? 'unknown'
}

export function groupLabelForType(type: SearchEntityType): string {
  switch (type) {
    case 'customer':
      return 'Clients'
    case 'supplier':
      return 'Fournisseurs'
    case 'relation':
      return 'Relations'
    case 'invoice':
      return 'Factures'
    case 'quote':
      return 'Devis'
    case 'credit_note':
      return 'Avoirs'
    case 'product':
    case 'service':
      return 'Catalogue'
    case 'accounting_entry':
      return 'Écritures'
    case 'vault_document':
    case 'document':
      return 'Documents'
    case 'organization':
      return 'Organisations'
    case 'user':
      return 'Utilisateurs'
    default:
      return 'Résultats'
  }
}

export function groupResultsByType(
  items: import('./types').SearchResult[],
): import('./types').SearchGroup[] {
  const order: string[] = []
  const map = new Map<string, import('./types').SearchResult[]>()
  for (const item of items) {
    const key = item.type
    if (!map.has(key)) {
      map.set(key, [])
      order.push(key)
    }
    map.get(key)!.push(item)
  }
  return order.map((id) => ({
    id,
    label: groupLabelForType(id as import('./types').SearchEntityType),
    type: id as import('./types').SearchEntityType,
    items: map.get(id)!,
  }))
}
