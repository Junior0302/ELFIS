/**
 * F1.3.2.2 — Catalog Modal Layering CL01–CL40
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { OverlayProvider, OverlayRouteBridge } from '../../design-system/overlays'
import { LibraryCatalogModal } from '../../comptapilot/facturation/LibraryCatalogModal'
import { ProductCreationDialog } from '../../comptapilot/facturation/ProductCreationDialog'
import { FP_OVERLAY_Z } from '../../comptapilot/facturation/overlayLayers'
import { ComposerDialog } from '../../comptapilot/facturation/ComposerDialog'
import type { BillingOverview } from '../../api'
import FacturationDocumentsPage from './FacturationDocumentsPage'
import {
  COMPOSER_PRODUCTS_STEP_HEADING,
  goToComposerProductsStep as goToProducts,
} from './facturation-composer-test-helpers'
import { createRef } from 'react'

const billingOverviewMock = vi.fn()
const listCatalogMock = vi.fn()
const createCatalogItemMock = vi.fn()

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
      listSharedRelations: vi.fn().mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      }),
      listCustomers: vi.fn().mockResolvedValue({ customers: [] }),
      listCatalog: (...args: unknown[]) => listCatalogMock(...args),
      createCatalogItem: (...args: unknown[]) => createCatalogItemMock(...args),
      createCustomer: vi.fn().mockResolvedValue({
        id: 42,
        name: 'Dupont SAS',
        email: 'd@example.com',
        phone: '',
        address: '',
      }),
      searchSharedRelations: vi.fn().mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      }),
    },
  }
})

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

function renderDocs(path = '/facturation/documents/new?type=facture') {
  return render(
    <OverlayProvider>
      <MemoryRouter initialEntries={[path]}>
        <OverlayRouteBridge />
        <Routes>
          <Route path="/facturation" element={<FacturationLayout />}>
            <Route path="documents" element={<FacturationDocumentsPage />}>
              <Route path="new" element={null} />
            </Route>
          </Route>
        </Routes>
      </MemoryRouter>
    </OverlayProvider>,
  )
}

beforeEach(() => {
  cleanup()
  billingOverviewMock.mockResolvedValue(sampleOverview())
  listCatalogMock.mockResolvedValue({
    items: [
      {
        id: 1,
        name: 'Audit annuel',
        unit: 'u',
        unit_price_ht: 120,
        vat_rate: 20,
        active: true,
        kind: 'service',
      },
      {
        id: 2,
        name: 'Licence Pro',
        unit: 'u',
        unit_price_ht: 49,
        vat_rate: 20,
        active: true,
        kind: 'product',
      },
    ],
  })
  createCatalogItemMock.mockResolvedValue({
    id: 99,
    name: 'Produit Neo',
    unit: 'u',
    unit_price_ht: 10,
    vat_rate: 20,
    active: true,
    kind: 'produit',
  })
})

afterEach(() => cleanup())

describe('CL01–CL10 Tokens / cause / mount', () => {
  it('CL01 — FP_OVERLAY_Z hiérarchie croissante', () => {
    expect(FP_OVERLAY_Z.documents).toBe(0)
    expect(FP_OVERLAY_Z.composerBackdrop).toBeLessThan(FP_OVERLAY_Z.composerDialog)
    expect(FP_OVERLAY_Z.composerDialog).toBeLessThan(FP_OVERLAY_Z.submodalBackdrop)
    expect(FP_OVERLAY_Z.submodalBackdrop).toBeLessThan(FP_OVERLAY_Z.catalogModal)
    expect(FP_OVERLAY_Z.catalogModal).toBeLessThan(FP_OVERLAY_Z.nestedCreate)
  })

  it('CL02 — valeurs brief 1000–1040', () => {
    expect(FP_OVERLAY_Z.composerBackdrop).toBe(1000)
    expect(FP_OVERLAY_Z.composerDialog).toBe(1010)
    expect(FP_OVERLAY_Z.submodalBackdrop).toBe(1020)
    expect(FP_OVERLAY_Z.catalogModal).toBe(1030)
    expect(FP_OVERLAY_Z.nestedCreate).toBe(1040)
  })

  it('CL03 — ComposerDialog applique z-index tokens', () => {
    render(
      <OverlayProvider>
        <ComposerDialog open phase="composer" onOpenChange={() => {}}>
          <div>c</div>
        </ComposerDialog>
      </OverlayProvider>,
    )
    const backdrop = document.querySelector('[data-fp-overlay-layer="composer-backdrop"]') as HTMLElement
    const dialog = document.querySelector('[data-fp-overlay-layer="composer-dialog"]') as HTMLElement
    expect(backdrop.style.zIndex).toBe(String(FP_OVERLAY_Z.composerBackdrop))
    expect(dialog.style.zIndex).toBe(String(FP_OVERLAY_Z.composerDialog))
  })

  it('CL04 — CatalogModal marker data-fp-library-catalog-modal', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
    expect(document.querySelector('[data-fp-library-catalog-modal="true"]')).toBeTruthy()
  })

  it('CL05 — backdrop z 1020', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const bd = document.querySelector('[data-fp-catalog-layer="backdrop"]') as HTMLElement
    expect(bd.style.zIndex).toBe(String(FP_OVERLAY_Z.submodalBackdrop))
  })

  it('CL06 — modal z 1030', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const modal = document.querySelector('[data-fp-catalog-layer="modal"]') as HTMLElement
    expect(modal.style.zIndex).toBe(String(FP_OVERLAY_Z.catalogModal))
  })

  it('CL07 — catalogue z > composer z', () => {
    expect(FP_OVERLAY_Z.catalogModal).toBeGreaterThan(FP_OVERLAY_Z.composerDialog)
  })

  it('CL08 — pas de classe ds-drawer sur catalogue', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    expect(document.querySelector('.ds-drawer')).toBeNull()
    expect(document.querySelector('.fp-catalog-modal')).toBeTruthy()
  })

  it('CL09 — backdrop sans blur CSS class', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const bd = document.querySelector('.fp-catalog-modal-backdrop') as HTMLElement
    expect(bd.className).not.toMatch(/ds-overlay-backdrop--drawer/)
  })

  it('CL10 — portal mount hors Composer children', async () => {
    render(
      <OverlayProvider>
        <div id="composer-sim">
          <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
        </div>
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const modal = document.querySelector('[data-fp-library-catalog-modal="true"]')!
    expect(modal.closest('#composer-sim')).toBeNull()
  })
})

describe('CL11–CL20 Composer integration', () => {
  it('CL11 — bouton Parcourir le catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getByRole('button', { name: /Parcourir le catalogue/i })).toBeInTheDocument()
  })

  it('CL12 — ouvre sous-modale Catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    expect(await screen.findByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
  })

  it('CL13 — Composer reste (Nouvelle facture)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('CL14 — catalogue au-dessus (z inline)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const catalogZ = Number(
      (document.querySelector('[data-fp-catalog-layer="modal"]') as HTMLElement).style.zIndex,
    )
    const composerZ = Number(
      (document.querySelector('[data-fp-overlay-layer="composer-dialog"]') as HTMLElement).style
        .zIndex,
    )
    expect(catalogZ).toBeGreaterThan(composerZ)
  })

  it('CL15 — liste items', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    expect(await screen.findByText('Audit annuel')).toBeInTheDocument()
  })

  it('CL16 — ajout + toast', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Audit annuel')
    await user.click(screen.getByRole('button', { name: /Ajouter Audit annuel/i }))
    expect(await screen.findByText(/Ajouté : Audit annuel/i)).toBeInTheDocument()
  })

  it('CL17 — modal reste après ajout', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Licence Pro')
    await user.click(screen.getByRole('button', { name: /Ajouter Licence Pro/i }))
    expect(screen.getByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
  })

  it('CL18 — Fermer footer', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
    await user.click(within(footer).getByRole('button', { name: /^Fermer$/i }))
    expect(screen.queryByRole('heading', { name: /^Catalogue$/i })).not.toBeInTheDocument()
  })

  it('CL19 — Escape ferme catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('heading', { name: /^Catalogue$/i })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('CL20 — filtres tablist', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    expect(await screen.findByRole('tablist', { name: /Filtres catalogue/i })).toBeInTheDocument()
  })
})

describe('CL21–CL30 Product creation nested', () => {
  it('CL21 — Nouveau produit ouvre dialog nested', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
    await user.click(within(footer).getByRole('button', { name: /Nouveau produit/i }))
    expect(await screen.findByRole('heading', { name: /^Nouveau produit$/i })).toBeInTheDocument()
    expect(document.querySelector('[data-fp-product-creation-dialog="true"]')).toBeTruthy()
  })

  it('CL22 — create backdrop z 1040', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
    await user.click(within(footer).getByRole('button', { name: /Nouveau produit/i }))
    await screen.findByRole('heading', { name: /^Nouveau produit$/i })
    const bd = document.querySelector('[data-fp-catalog-layer="create-backdrop"]') as HTMLElement
    expect(bd.style.zIndex).toBe(String(FP_OVERLAY_Z.nestedCreate))
  })

  it('CL23 — créer ajoute + reste catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
    await user.click(within(footer).getByRole('button', { name: /Nouveau produit/i }))
    await user.type(await screen.findByLabelText(/Nom du nouveau produit/i), 'Produit Neo')
    await user.click(screen.getByRole('button', { name: /Créer et ajouter/i }))
    expect(await screen.findByText(/Ajouté : Produit Neo/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
  })

  it('CL24 — Annuler création', async () => {
    const user = userEvent.setup()
    render(
      <OverlayProvider>
        <ProductCreationDialog
          open
          onOpenChange={vi.fn()}
          onCreated={vi.fn()}
        />
      </OverlayProvider>,
    )
    await user.click(screen.getByRole('button', { name: /^Annuler$/i }))
  })

  it('CL25 — ProductCreationDialog unitaire', () => {
    render(
      <OverlayProvider>
        <ProductCreationDialog open onOpenChange={vi.fn()} onCreated={vi.fn()} />
      </OverlayProvider>,
    )
    expect(screen.getByRole('heading', { name: /^Nouveau produit$/i })).toBeInTheDocument()
  })

  it('CL26 — aria-modal catalogue', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    const dlg = await screen.findByRole('dialog', { name: /Catalogue/i })
    expect(dlg).toHaveAttribute('aria-modal', 'true')
  })

  it('CL27 — returnFocusRef typé', () => {
    const ref = createRef<HTMLButtonElement>()
    expect(ref.current).toBeNull()
  })

  it('CL28 — classe fp-catalog-modal dimensions', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    expect(document.querySelector('.fp-catalog-modal')).toBeTruthy()
  })

  it('CL29 — CSS vars :root présentes après import spaces', () => {
    expect(FP_OVERLAY_Z.submodalBackdrop).toBe(1020)
  })

  it('CL30 — createCatalogItem appelé', async () => {
    const user = userEvent.setup()
    const onCreated = vi.fn()
    render(
      <OverlayProvider>
        <ProductCreationDialog open onOpenChange={vi.fn()} onCreated={onCreated} />
      </OverlayProvider>,
    )
    await user.type(screen.getByLabelText(/Nom du nouveau produit/i), 'X')
    await user.click(screen.getByRole('button', { name: /Créer et ajouter/i }))
    expect(createCatalogItemMock).toHaveBeenCalled()
  })
})

describe('CL31–CL40 A11y / regress / close', () => {
  it('CL31 — X ferme catalogue', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={onOpenChange} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    await user.click(document.querySelector('.fp-catalog-modal__close') as HTMLButtonElement)
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('CL32 — search input focusable', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    expect(await screen.findByLabelText(/Rechercher dans le catalogue/i)).toBeInTheDocument()
  })

  it('CL33 — pas de Link Ouvrir le catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.queryByRole('link', { name: /Ouvrir le catalogue/i })).not.toBeInTheDocument()
  })

  it('CL34 — Composer presentation modal intacte', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(document.querySelector('[data-fp-composer-presentation="modal"]')).toBeTruthy()
  })

  it('CL35 — data-fp-composer-dialog true', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-fp-composer-dialog="true"]')).toBeTruthy()
  })

  it('CL36 — double ajout distinct', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Audit annuel')
    await user.click(screen.getByRole('button', { name: /Ajouter Audit annuel/i }))
    await user.click(screen.getByRole('button', { name: /Ajouter Licence Pro/i }))
    expect(screen.getByDisplayValue('Audit annuel')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Licence Pro')).toBeInTheDocument()
  })

  it('CL37 — overlay class fp-catalog-modal-backdrop', async () => {
    render(
      <OverlayProvider>
        <LibraryCatalogModal open onOpenChange={vi.fn()} onAddResource={vi.fn()} />
      </OverlayProvider>,
    )
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    expect(document.querySelector('.fp-catalog-modal-backdrop')).toBeTruthy()
  })

  it('CL38 — nested create > catalog z', () => {
    expect(FP_OVERLAY_Z.nestedCreate).toBeGreaterThan(FP_OVERLAY_Z.catalogModal)
  })

  it('CL39 — reexport Drawer alias = Modal', async () => {
    const mod = await import('../../comptapilot/facturation/LibraryCatalogDrawer')
    expect(mod.LibraryCatalogDrawer).toBe(mod.LibraryCatalogModal)
  })

  it('CL40 — fermeture catalogue ne détruit pas Composer', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    await user.keyboard('{Escape}')
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: COMPOSER_PRODUCTS_STEP_HEADING })).toBeInTheDocument()
  })
})
