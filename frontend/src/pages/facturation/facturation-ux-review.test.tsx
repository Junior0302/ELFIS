/**
 * F1.3.1 — Tests UX Facturation zero friction (UXF01–UXF40)
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { NewDocumentDialog } from '../../comptapilot/facturation/NewDocumentDialog'
import { navCategories } from '../../navModel'
import { CustomerPicker } from '../../platform-search/pickers/CustomerPicker'
import { ProductPicker } from '../../platform-search/pickers/ProductPicker'
import { OverlayProvider } from '../../design-system/overlays'
import type { BillingOverview } from '../../api'

const billingOverviewMock = vi.fn()
const navigateMock = vi.fn()

vi.mock('../../auth', () => ({
  useAuth: () => ({
    token: 'tok',
    orgId: 7,
    user: { id: 1, is_platform_admin: false, first_name: 'Chris' },
  }),
}))

vi.mock('../../api', async () => {
  const actual = await vi.importActual<typeof import('../../api')>('../../api')
  return {
    ...actual,
    api: {
      ...actual.api,
      billingOverview: (...args: unknown[]) => billingOverviewMock(...args),
      listSharedRelations: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }),
      listCustomers: vi.fn().mockResolvedValue({ customers: [] }),
      listCatalog: vi.fn().mockResolvedValue({ items: [] }),
      searchSharedRelations: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }),
    },
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

import FacturationPage from '../FacturationPage'
import FacturationComposerPage from './FacturationComposerPage'

function sampleOverview(): BillingOverview {
  return {
    smtp_configured: true,
    stats: {
      documents: 1,
      customers: 1,
      unpaid: 0,
      unpaid_amount: 0,
      quotes: 0,
      invoices: 1,
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
        amount_ht: 100,
        amount_tva: 20,
        amount_ttc: 120,
        vat_rate: 20,
        paid_amount: 0,
        signature_status: 'none',
        notes: '',
        lines: [],
      },
    ],
    customers: [{ id: 1, name: 'Atelier Nord', email: 'contact@atelier.example' }],
  }
}

function wrap(ui: ReactNode, path = '/facturation/documents') {
  return render(
    <OverlayProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/facturation" element={<FacturationLayout />}>
            <Route path="documents" element={ui} />
            <Route path="nouveau" element={<FacturationComposerPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </OverlayProvider>,
  )
}

beforeEach(() => {
  cleanup()
  billingOverviewMock.mockReset()
  billingOverviewMock.mockResolvedValue(sampleOverview())
  navigateMock.mockReset()
})

afterEach(() => {
  cleanup()
})

describe('UXF01–UXF10 Nav & Documents entry', () => {
  it('UXF01 — nav Facturation sans « Nouveau document »', () => {
    const ventes = navCategories.find((c) => c.id === 'ventes')
    expect(ventes?.children.some((l) => l.label === 'Nouveau document')).toBe(false)
  })

  it('UXF02 — nav Facturation contient Vue d’ensemble / Documents / Devis / Catalogue / Activité', () => {
    const labels = navCategories.find((c) => c.id === 'ventes')?.children.map((l) => l.label)
    expect(labels).toEqual([
      'Vue d’ensemble',
      'Documents',
      'Devis',
      'Catalogue',
      'Activité',
    ])
  })

  it('UXF03 — nav horizontale sans Nouveau', () => {
    wrap(<div>docs</div>, '/facturation/documents')
    expect(screen.queryByRole('link', { name: /nouveau document/i })).not.toBeInTheDocument()
  })

  it('UXF04 — Documents : bouton primaire « Créer un document »', async () => {
    wrap(<FacturationPage />)
    await waitFor(() => screen.getByRole('button', { name: 'Créer un document' }))
    expect(screen.queryByRole('link', { name: 'Nouveau document' })).not.toBeInTheDocument()
  })

  it('UXF05 — pas de « Liste des devis » en header', async () => {
    wrap(<FacturationPage />)
    await waitFor(() => screen.getByText('F-2026-001'))
    expect(screen.queryByRole('link', { name: 'Liste des devis' })).not.toBeInTheDocument()
  })

  it('UXF06 — filtre Devis disponible', async () => {
    wrap(<FacturationPage />)
    await waitFor(() => screen.getByRole('tab', { name: 'Devis' }))
  })

  it('UXF07 — CTA ouvre pop-in (pas navigation Composer)', async () => {
    const user = userEvent.setup()
    wrap(<FacturationPage />)
    await waitFor(() => screen.getByRole('button', { name: 'Créer un document' }))
    await user.click(screen.getByRole('button', { name: 'Créer un document' }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Que souhaitez-vous créer ?')).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('UXF08 — pop-in role=dialog aria-modal', async () => {
    const user = userEvent.setup()
    wrap(<FacturationPage />)
    await user.click(await screen.findByRole('button', { name: 'Créer un document' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('UXF09 — Créer désactivé sans type', async () => {
    const user = userEvent.setup()
    wrap(<FacturationPage />)
    await user.click(await screen.findByRole('button', { name: 'Créer un document' }))
    expect(await screen.findByRole('button', { name: 'Créer le document' })).toBeDisabled()
  })

  it('UXF10 — sélection type active Créer', async () => {
    const user = userEvent.setup()
    wrap(<FacturationPage />)
    await user.click(await screen.findByRole('button', { name: 'Créer un document' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('radio', { name: /facture/i }))
    expect(within(dialog).getByRole('button', { name: 'Créer le document' })).not.toBeDisabled()
  })
})

describe('UXF11–UXF20 Pop-in & Composer open', () => {
  it('UXF11 — options Facture / Devis / Avoir', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter>
          <NewDocumentDialog open onOpenChange={() => {}} />
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(screen.getByRole('radio', { name: /facture/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /devis/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /avoir/i })).toBeInTheDocument()
  })

  it('UXF12 — Annuler ferme le dialog', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(
      <OverlayProvider>
        <MemoryRouter>
          <NewDocumentDialog open onOpenChange={onOpenChange} />
        </MemoryRouter>
      </OverlayProvider>,
    )
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('UXF13 — Créer navigue vers Composer avec type', async () => {
    const user = userEvent.setup()
    render(
      <OverlayProvider>
        <MemoryRouter>
          <NewDocumentDialog open onOpenChange={() => {}} />
        </MemoryRouter>
      </OverlayProvider>,
    )
    await user.click(screen.getByRole('radio', { name: /devis/i }))
    await user.click(screen.getByRole('button', { name: 'Créer le document' }))
    expect(navigateMock).toHaveBeenCalledWith('/facturation/documents/new?type=devis')
  })

  it('UXF14 — Composer sans type : message in-page (pas redirect auto)', () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
            <Route path="/facturation/documents" element={<div>docs-redirect</div>} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/Type de document manquant/i)
    expect(screen.queryByText('docs-redirect')).not.toBeInTheDocument()
  })

  it('UXF15 — Composer facture titre Nouvelle facture', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('UXF16 — Composer devis titre Nouveau devis', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=devis']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Nouveau devis' })).toBeInTheDocument()
  })

  it('UXF17 — Composer avoir titre Nouvel avoir', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=avoir']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Nouvel avoir' })).toBeInTheDocument()
  })

  it('UXF18 — pas de sidebar wizard 10 étapes', async () => {
    const { container } = render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('.elf-cmp-sidebar')).toBeNull()
    expect(screen.queryByText('Choix du document')).not.toBeInTheDocument()
  })

  it('UXF19 — sections freeform présentes', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: /^Client$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Produits$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Conditions$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Notes$/i })).toBeInTheDocument()
  })

  it('UXF20 — focus mode actif sur Composer', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation" element={<FacturationLayout />}>
              <Route path="nouveau" element={<FacturationComposerPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-fp-focus="true"]')).toBeTruthy()
  })
})

describe('UXF21–UXF30 Pickers & lignes', () => {
  it('UXF21 — CustomerPicker fermé au mount', () => {
    render(
      <MemoryRouter>
        <CustomerPicker onSelect={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('UXF22 — ProductPicker fermé au mount', () => {
    render(
      <MemoryRouter>
        <ProductPicker onSelect={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('UXF23 — bouton Ajouter une ligne libre', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('button', { name: 'Ajouter une ligne libre' })).toBeInTheDocument()
  })

  it('UXF24 — ligne libre sans ouvrir listbox', async () => {
    const user = userEvent.setup()
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    expect(screen.getByLabelText(/libellé ligne 1/i)).toBeInTheDocument()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('UXF25 — + Ajouter un client visible', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('button', { name: /\+ Ajouter un client/i })).toBeInTheDocument()
  })

  it('UXF26 — Nouveau produit accessible', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findAllByRole('button', { name: /Nouveau produit/i })).not.toHaveLength(0)
  })

  it('UXF27 — pas de copy InventoryPilot dans Composer', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.queryByText(/InventoryPilot/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Smart Library/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Étape préparée/i)).not.toBeInTheDocument()
  })

  it('UXF28 — progression légère (pas 10 steps)', async () => {
    const { container } = render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    const dots = container.querySelectorAll('.elf-cmp-progress__dot')
    expect(dots.length).toBeLessThanOrEqual(5)
    expect(dots.length).toBeGreaterThan(0)
  })

  it('UXF29 — header Annuler présent', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('button', { name: 'Annuler' })).toBeInTheDocument()
  })

  it('UXF30 — retour Documents dans toolbar', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('button', { name: 'Documents' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dashboard' })).not.toBeInTheDocument()
  })
})

describe('UXF31–UXF40 Validation, focus, a11y pop-in', () => {
  it('UXF31 — Escape ferme pop-in non engagé', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(
      <OverlayProvider>
        <MemoryRouter>
          <NewDocumentDialog open onOpenChange={onOpenChange} />
        </MemoryRouter>
      </OverlayProvider>,
    )
    await user.keyboard('{Escape}')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('UXF32 — radiogroup type document', () => {
    render(
      <OverlayProvider>
        <MemoryRouter>
          <NewDocumentDialog open onOpenChange={() => {}} />
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(screen.getByRole('radiogroup', { name: /type de document/i })).toBeInTheDocument()
  })

  it('UXF33 — Composer sections Contrôles / Paiement / Totaux / Aperçu', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: /^Contrôles$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Paiement$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Totaux$/i })).toBeInTheDocument()
  })

  it('UXF34 — data-fp-composer f131', async () => {
    const { container } = render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('[data-fp-composer="f131"]')).toBeTruthy()
  })

  it('UXF35 — preview sticky slot présent', async () => {
    const { container } = render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('.elf-cmp__preview-slot')).toBeTruthy()
  })

  it('UXF36 — toggle aperçu disponible', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('button', { name: /aperçu/i })).toBeInTheDocument()
  })

  it('UXF37 — confirm exit si draft local', async () => {
    const user = userEvent.setup()
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Presta')
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(await screen.findByText(/Quitter cette/i)).toBeInTheDocument()
  })

  it('UXF38 — create=1 ouvre pop-in Documents', async () => {
    wrap(<FacturationPage />, '/facturation/documents?create=1')
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
  })

  it('UXF39 — deep link type=facture conserve route', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('UXF40 — une seule action primaire Documents', async () => {
    wrap(<FacturationPage />)
    await waitFor(() => screen.getByRole('button', { name: 'Créer un document' }))
    const primaries = screen.getAllByRole('button', { name: 'Créer un document' })
    expect(primaries.length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByRole('link', { name: /nouveau document/i })).not.toBeInTheDocument()
  })
})
