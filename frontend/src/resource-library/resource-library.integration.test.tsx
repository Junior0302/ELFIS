/**
 * Resource Library — integration smoke (Smart Library UI)
 * @vitest-environment jsdom
 */
import type { ReactElement } from 'react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SmartLibraryPage from './ui/SmartLibraryPage'

vi.mock('../auth', () => ({
  useAuth: () => ({
    token: 'test-token',
    orgId: 1,
    memberships: [
      {
        membership_id: 1,
        organization_id: 1,
        organization_name: 'Org',
        role: 'owner',
        permissions: ['*', 'invoice.read', 'invoice.create'],
        plan: 'pro',
        country: 'FR',
      },
    ],
  }),
}))

vi.mock('../api', () => ({
  formatEuro: (n: number) => `${n.toFixed(2)} €`,
  api: {
    listCatalog: vi.fn(async () => ({
      items: [
        {
          id: 1,
          name: 'Licence ELFIS',
          kind: 'service',
          unit: 'mois',
          unit_price_ht: 99,
          vat_rate: 20,
          active: true,
        },
      ],
    })),
    createCatalogItem: vi.fn(),
    updateCatalogItem: vi.fn(),
    deleteCatalogItem: vi.fn(),
  },
}))

function wrap(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('Smart Library page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    cleanup()
  })

  it('affiche le hero et une carte ressource', async () => {
    wrap(<SmartLibraryPage />)
    expect(screen.getByRole('heading', { name: /smart library/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('Licence ELFIS')).toBeInTheDocument()
    })
    expect(screen.getByRole('navigation', { name: /sections smart library/i })).toBeInTheDocument()
  })

  it('sections meta marquées bientôt / désactivées', async () => {
    wrap(<SmartLibraryPage />)
    await waitFor(() => screen.getByText('Licence ELFIS'))
    const nav = screen.getByRole('navigation', { name: /sections smart library/i })
    const fav = within(nav).getByRole('button', { name: /favoris/i })
    expect(fav).toBeDisabled()
  })
})
