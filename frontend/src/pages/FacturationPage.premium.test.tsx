/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { BillingOverview } from '../api'

const billingOverviewMock = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => ({
    token: 'tok',
    orgId: 7,
    user: { id: 1, is_platform_admin: false, first_name: 'Chris' },
  }),
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    api: {
      ...actual.api,
      billingOverview: (...args: unknown[]) => billingOverviewMock(...args),
    },
  }
})

import FacturationPage from './FacturationPage'

function sampleOverview(over: Partial<BillingOverview> = {}): BillingOverview {
  return {
    smtp_configured: true,
    stats: {
      documents: 3,
      customers: 2,
      unpaid: 1,
      unpaid_amount: 420,
      quotes: 1,
      invoices: 2,
      credits: 0,
    },
    documents: [
      {
        id: 11,
        number: 'F-2026-001',
        doc_type: 'facture',
        status: 'sent',
        customer_name: 'Atelier Nord',
        customer_email: 'contact@atelier.example',
        issue_date: '2026-08-01',
        due_date: '2026-08-31',
        amount_ht: 350,
        amount_tva: 70,
        amount_ttc: 420,
        vat_rate: 20,
        paid_amount: 0,
        signature_status: 'none',
        notes: '',
        lines: [],
      },
    ],
    customers: [{ id: 1, name: 'Atelier Nord', email: 'contact@atelier.example' }],
    ...over,
  }
}

describe('FacturationPage premium P0.5', () => {
  beforeEach(() => {
    cleanup()
    billingOverviewMock.mockReset()
    billingOverviewMock.mockResolvedValue(sampleOverview())
  })

  afterEach(() => {
    cleanup()
  })

  it('expose le marqueur fp05, header premium et KPI réels', async () => {
    const { container } = render(
      <MemoryRouter>
        <FacturationPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(container.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
    })

    expect(screen.getByRole('heading', { name: 'Facturation', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('ComptaPilot · Facturation')).toBeInTheDocument()
    expect(screen.getByText('Envoi e-mail prêt')).toBeInTheDocument()
    expect(screen.getByText('Essentiel')).toBeInTheDocument()
    expect(screen.getByText('Suivre')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Créer un document' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Liste des devis' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nouveau document' })).not.toBeInTheDocument()

    const unpaid = screen.getByText('Impayés').closest('.fp-kpi')
    expect(unpaid?.querySelector('.fp-kpi__value')?.textContent).toBe('1')
    const due = screen.getByText('Montant dû').closest('.fp-kpi')
    expect(due?.className).toMatch(/fp-kpi--emphasis/)
    expect(due?.textContent).toMatch(/420/)
  })

  it('conserve le tableau documents et les actions de base', async () => {
    render(
      <MemoryRouter>
        <FacturationPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('F-2026-001')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: 'Visualiser' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Payer' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Devis' })).toBeInTheDocument()
  })
})
