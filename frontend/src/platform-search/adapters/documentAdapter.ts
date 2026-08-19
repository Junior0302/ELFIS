/**
 * Catalogue local / SalesDoc → SearchResult.
 */

import type { CatalogItem, SalesDoc } from '../../api'
import type { SearchEntityType, SearchResult } from '../types'

export function catalogItemToSearchResult(item: CatalogItem): SearchResult {
  const type: SearchEntityType = item.kind === 'service' ? 'service' : 'product'
  return {
    type,
    id: String(item.id),
    title: item.name,
    subtitle: `${item.unit_price_ht.toFixed(2)} € HT · TVA ${item.vat_rate}%`,
    description: item.unit ? `Unité : ${item.unit}` : undefined,
    status: item.active ? 'active' : 'inactive',
    route: '/catalogue',
    source: 'billing_catalog',
    metadata: {
      catalogItemId: item.id,
      kind: item.kind,
      unit: item.unit,
      unit_price_ht: item.unit_price_ht,
      vat_rate: item.vat_rate,
      active: item.active,
    },
    actions: [{ id: 'select', label: 'Sélectionner', kind: 'select' }],
  }
}

function salesDocType(docType: string): SearchEntityType {
  const t = docType.toLowerCase()
  if (t === 'invoice' || t === 'facture') return 'invoice'
  if (t === 'quote' || t === 'devis') return 'quote'
  if (t === 'credit' || t === 'credit_note' || t === 'avoir') return 'credit_note'
  return 'document'
}

export function salesDocToSearchResult(doc: SalesDoc): SearchResult {
  const type = salesDocType(doc.doc_type)
  return {
    type,
    id: String(doc.id),
    title: doc.number || `${doc.doc_type} #${doc.id}`,
    subtitle: doc.customer_name,
    description: `${doc.amount_ttc.toFixed(2)} € TTC · ${doc.status}`,
    status: doc.status,
    route: `/facturation/documents/${doc.id}`,
    source: 'billing_sales_documents',
    metadata: {
      docId: doc.id,
      doc_type: doc.doc_type,
      customer_id: doc.customer_id,
      amount_ttc: doc.amount_ttc,
    },
    actions: [
      { id: 'select', label: 'Sélectionner', kind: 'select' },
      {
        id: 'open',
        label: 'Ouvrir',
        kind: 'navigate',
        href: `/facturation/documents/${doc.id}`,
      },
    ],
  }
}
