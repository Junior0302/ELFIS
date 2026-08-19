import { describe, expect, it } from 'vitest'
import type { SalesDoc } from './api'
import { buildDuplicateSalesDocPayload } from './salesDocDuplicate'

const baseDoc: SalesDoc & { customer_id?: number | null } = {
  id: 12,
  doc_type: 'devis',
  number: 'DEV-2026-0003',
  issue_date: '01-08-2026',
  due_date: '31-08-2026',
  status: 'sent',
  customer_name: 'Client Demo',
  customer_email: 'demo@client.fr',
  amount_ht: 100,
  amount_tva: 20,
  amount_ttc: 120,
  vat_rate: 20,
  paid_amount: 0,
  signature_status: 'none',
  notes: 'Conditions net 30',
  customer_id: 7,
  lines: [{ label: 'Audit', quantity: 2, unit_price: 50, catalog_item_id: 3 }],
}

describe('buildDuplicateSalesDocPayload', () => {
  it('copie client, lignes et crée une note de provenance', () => {
    const payload = buildDuplicateSalesDocPayload(baseDoc)
    expect(payload.doc_type).toBe('devis')
    expect(payload.customer_name).toBe('Client Demo')
    expect(payload.customer_id).toBe(7)
    expect(payload.amount_ht).toBe(100)
    expect(payload.lines).toHaveLength(1)
    expect(payload.notes).toContain('Copie de DEV-2026-0003')
    expect(payload.notes).toContain('Conditions net 30')
  })

  it('fonctionne sans lignes_json via fallback HT', () => {
    const payload = buildDuplicateSalesDocPayload({
      ...baseDoc,
      lines: undefined,
      notes: '',
    })
    expect(payload.lines[0]?.label).toBe('Prestation')
    expect(payload.amount_ht).toBe(100)
    expect(payload.notes).toBe('Copie de DEV-2026-0003')
  })
})
