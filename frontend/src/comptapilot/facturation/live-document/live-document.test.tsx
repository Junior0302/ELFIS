/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import {
  deriveLiveDocumentInsights,
  deriveLiveDocumentStatus,
  formatDueDateLabel,
  LiveTotals,
  snapshotLiveTotals,
  STANDARD_FR_VAT_RATES,
} from './index'
import { createEmptyFacturationDraft } from '../workflow'

describe('Live Document Experience V1 — helpers', () => {
  it('calcule totaux + échéance calendaire sans inventer', () => {
    const draft = createEmptyFacturationDraft({
      products: [
        {
          catalogItemId: 1,
          label: 'A',
          quantity: 2,
          unitPrice: 100,
          vatRate: 20,
          discountPercent: 10,
        },
      ],
      vatRate: 20,
      dueDays: 30,
    })
    const snap = snapshotLiveTotals(draft, new Date('2026-08-02T12:00:00Z'))
    expect(snap.ht).toBe(180)
    expect(snap.discountTotal).toBe(20)
    expect(snap.tva).toBe(36)
    expect(snap.ttc).toBe(216)
    expect(snap.dueDays).toBe(30)
    expect(formatDueDateLabel(0, new Date('2026-08-02'))).toMatch(/02/)
  })

  it('dérive statut prêt / validation / envoyé / erreur', () => {
    const base = {
      createdDocId: 1 as number | null,
      sent: false,
      issues: [] as { id: string; severity: 'info' | 'warning' | 'error' | 'suggestion'; message: string }[],
      autosave: { status: 'idle' as const },
      hasDocType: true,
      hasClient: true,
      hasProducts: true,
    }
    expect(deriveLiveDocumentStatus(base).status).toBe('ready')
    expect(
      deriveLiveDocumentStatus({
        ...base,
        issues: [{ id: 'x', severity: 'warning', message: 'Manque client' }],
      }).status,
    ).toBe('validation_required')
    expect(deriveLiveDocumentStatus({ ...base, sent: true }).status).toBe('sent')
    expect(
      deriveLiveDocumentStatus({
        ...base,
        autosave: { status: 'error', message: 'fail' },
      }).status,
    ).toBe('error')
  })

  it('génère insights live uniquement depuis données réelles', () => {
    const draft = createEmptyFacturationDraft({
      client: {
        customerId: 1,
        relationId: null,
        displayName: 'Acme',
        email: 'a@b.c',
        source: 'billing_customer',
      },
      products: [
        {
          catalogItemId: 9,
          label: 'Nouveau',
          quantity: 1,
          unitPrice: 60_000,
          vatRate: 20,
          catalogCreatedAt: '2026-07-20T00:00:00Z',
        },
      ],
      vatRate: 12,
    })
    const insights = deriveLiveDocumentInsights({
      draft,
      issues: [],
      now: Date.parse('2026-08-02T00:00:00Z'),
    })
    const ids = insights.map((i) => i.id)
    expect(ids).not.toContain('live:client-selected')
    expect(ids).not.toContain('live:product-added')
    expect(ids).toContain('live:vat-unusual')
    expect(ids).toContain('live:amount-high')
    expect(ids).toContain('live:product-recent')
    expect(ids.some((id) => id.includes('similar'))).toBe(false)
    expect(STANDARD_FR_VAT_RATES).toContain(20)
  })

  it('n’invente pas produit récent sans catalogCreatedAt', () => {
    const draft = createEmptyFacturationDraft({
      products: [
        {
          catalogItemId: 1,
          label: 'Ancien',
          quantity: 1,
          unitPrice: 10,
          vatRate: 20,
        },
      ],
      vatRate: 20,
    })
    const insights = deriveLiveDocumentInsights({ draft, issues: [] })
    expect(insights.some((i) => i.id === 'live:product-recent')).toBe(false)
  })

  it('rend LiveTotals avec aria-live', () => {
    const totals = snapshotLiveTotals(
      createEmptyFacturationDraft({
        products: [{ catalogItemId: null, label: 'X', quantity: 1, unitPrice: 50, vatRate: 20 }],
        vatRate: 20,
        dueDays: 15,
      }),
    )
    render(<LiveTotals totals={totals} vatRate={20} />)
    expect(screen.getByRole('status', { name: /totaux/i })).toBeInTheDocument()
    expect(screen.getByText(/Total TTC/i)).toBeInTheDocument()
    cleanup()
  })
})
