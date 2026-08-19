/**
 * Platform Search — RTL pickers PSS13–PSS18
 * @vitest-environment jsdom
 */
import { describe, expect, it, afterEach, vi, beforeEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { CustomerPicker } from './pickers/CustomerPicker'
import { ProductPicker } from './pickers/ProductPicker'
import { DocumentPicker } from './pickers/DocumentPicker'
import { SupplierPicker } from './pickers/SupplierPicker'

const searchSharedRelations = vi.fn()
const listSharedRelations = vi.fn()
const listCustomers = vi.fn()
const listCatalog = vi.fn()
const billingOverview = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => ({
    token: 't',
    orgId: 1,
    user: { id: 1, email: 'a@b.c' },
    memberships: [],
    loading: false,
    firebaseReady: true,
  }),
}))

vi.mock('../api', () => ({
  api: {
    searchSharedRelations: (...a: unknown[]) => searchSharedRelations(...a),
    listSharedRelations: (...a: unknown[]) => listSharedRelations(...a),
    listCustomers: (...a: unknown[]) => listCustomers(...a),
    listCatalog: (...a: unknown[]) => listCatalog(...a),
    billingOverview: (...a: unknown[]) => billingOverview(...a),
    createCustomer: vi.fn(),
    searchElfis: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0, execution_time_ms: 1 }),
  },
}))

function wrap(ui: ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

beforeEach(() => {
  searchSharedRelations.mockReset()
  listSharedRelations.mockReset()
  listCustomers.mockReset()
  listCatalog.mockReset()
  billingOverview.mockReset()

  listSharedRelations.mockResolvedValue({
    items: [
      {
        id: 'customer:1',
        organization_id: 1,
        party_type: 'organization',
        display_name: 'Rel Client',
        legal_name: 'Rel Client',
        first_name: '',
        last_name: '',
        emails: ['r@x.fr'],
        phones: [],
        addresses: [],
        tax_number: '',
        siren: '',
        siret: '',
        roles: ['customer'],
        status: 'active',
        source_system: 'customer',
        source_entity_id: 1,
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
    total_pages: 1,
  })
  listCustomers.mockResolvedValue({
    customers: [
      {
        id: 99,
        name: 'Billing Client',
        email: 'b@x.fr',
        phone: '',
        address: '',
        vat_number: '',
      },
    ],
  })
  listCatalog.mockResolvedValue({ items: [] })
  billingOverview.mockResolvedValue({
    stats: { documents: 0, customers: 0, unpaid: 0, unpaid_amount: 0, quotes: 0, invoices: 0, credits: 0 },
    documents: [
      {
        id: 7,
        doc_type: 'invoice',
        number: 'F-7',
        issue_date: '',
        due_date: '',
        status: 'sent',
        customer_name: 'Acme',
        customer_email: '',
        amount_ht: 100,
        amount_tva: 20,
        amount_ttc: 120,
        vat_rate: 20,
        paid_amount: 0,
        signature_status: '',
        notes: '',
      },
    ],
    customers: [],
  })
  searchSharedRelations.mockResolvedValue({
    items: [
      {
        id: 'customer:1',
        organization_id: 1,
        party_type: 'organization',
        display_name: 'Rel Client',
        legal_name: 'Rel Client',
        first_name: '',
        last_name: '',
        emails: ['r@x.fr'],
        phones: [],
        addresses: [],
        tax_number: '',
        siren: '',
        siret: '',
        roles: ['customer'],
        status: 'active',
        source_system: 'customer',
        source_entity_id: 1,
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
    total_pages: 1,
  })
})

afterEach(() => {
  cleanup()
})

describe('PSS13–PSS15 CustomerPicker', () => {
  it('rend un combobox fermé par défaut (pas de liste au mount)', async () => {
    wrap(<CustomerPicker onSelect={() => {}} />)
    expect(screen.getByRole('combobox', { name: /client/i })).toBeInTheDocument()
    expect(listSharedRelations).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('sélectionne SharedRelation après recherche', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    wrap(<CustomerPicker onSelect={onSelect} />)
    const input = screen.getByRole('combobox', { name: /client/i })
    await user.click(input)
    await user.type(input, 'Rel')
    await waitFor(() => screen.getByText('Rel Client'))
    await user.click(screen.getByText('Rel Client'))
    expect(onSelect).toHaveBeenCalled()
    expect(onSelect.mock.calls[0][0].relationId).toBe('customer:1')
    expect(onSelect.mock.calls[0][0].source).toBe('shared_relation')
  })

  it('expose fallback billing après recherche', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    wrap(<CustomerPicker onSelect={onSelect} />)
    const input = screen.getByRole('combobox', { name: /client/i })
    await user.type(input, 'Bill')
    await waitFor(() => screen.getByText('Billing Client'))
    await user.click(screen.getByText('Billing Client'))
    expect(onSelect.mock.calls[0][0].customerId).toBe(99)
    expect(onSelect.mock.calls[0][0].source).toBe('billing_customer')
  })
})

describe('PSS16 ProductPicker empty', () => {
  it('empty honnête après recherche', async () => {
    const user = userEvent.setup()
    wrap(<ProductPicker onSelect={() => {}} />)
    expect(listCatalog).not.toHaveBeenCalled()
    const input = screen.getByRole('combobox', { name: /produit/i })
    await user.type(input, 'xyz')
    await waitFor(() => expect(listCatalog).toHaveBeenCalled())
    expect(await screen.findByText(/aucun produit/i)).toBeInTheDocument()
  })
})

describe('PSS17 DocumentPicker', () => {
  it('liste via billingOverview', async () => {
    wrap(<DocumentPicker onSelect={() => {}} />)
    await waitFor(() => expect(billingOverview).toHaveBeenCalled())
    expect(await screen.findByText('F-7')).toBeInTheDocument()
  })
})

describe('PSS18 SupplierPicker', () => {
  it('n’appelle pas SharedRelations au mount (fermé)', async () => {
    listSharedRelations.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    })
    wrap(<SupplierPicker onSelect={() => {}} />)
    expect(listSharedRelations).not.toHaveBeenCalled()
  })
})
