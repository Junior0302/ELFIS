import type { SalesDoc } from './api'
import { normalizeSalesLines, salesLinesFromDoc } from './salesDocLines'

/** Payload POST /billing/documents pour dupliquer un devis (ou autre doc) en brouillon. */
export function buildDuplicateSalesDocPayload(doc: SalesDoc & { customer_id?: number | null }) {
  const lines = normalizeSalesLines(salesLinesFromDoc(doc.lines, doc.amount_ht))
  const amount_ht =
    lines.length > 0
      ? Math.round(lines.reduce((s, l) => s + l.quantity * l.unit_price, 0) * 100) / 100
      : doc.amount_ht
  const noteBase = (doc.notes || '').trim()
  const dupNote = `Copie de ${doc.number}`
  return {
    doc_type: doc.doc_type,
    customer_name: doc.customer_name,
    customer_email: doc.customer_email || '',
    customer_id: doc.customer_id ?? null,
    amount_ht,
    vat_rate: doc.vat_rate,
    notes: noteBase ? `${noteBase}\n${dupNote}` : dupNote,
    lines,
  }
}
