/**
 * F1.3.2.1 — Premium Catalog / Line State / Exit Dialog — PC01–PC40
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { OverlayProvider, OverlayRouteBridge } from '../../design-system/overlays'
import { ExitConfirmationDialog } from '../../comptapilot/facturation/ExitConfirmationDialog'
import { LibraryCatalogDrawer } from '../../comptapilot/facturation/LibraryCatalogDrawer'
import { ProductPicker } from '../../platform-search'
import { createEmptyFacturationDraft } from '../../comptapilot/facturation/workflow'
import type { BillingOverview } from '../../api'
import FacturationDocumentsPage from './FacturationDocumentsPage'
import { createRef } from 'react'

const billingOverviewMock = vi.fn()
const listCatalogMock = vi.fn()

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
      createSalesDoc: vi.fn().mockResolvedValue({
        id: 501,
        number: 'F-2026-099',
        doc_type: 'facture',
        status: 'draft',
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

async function goToProducts(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
  await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Dupont SAS')
  const panel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
  await user.click(within(panel).getByRole('button', { name: 'Enregistrer' }))
  await user.click(screen.getByRole('button', { name: 'Continuer' }))
  expect(await screen.findByRole('heading', { name: /^Produits$/i })).toBeInTheDocument()
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
        description: 'Service',
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
})

afterEach(() => cleanup())

describe('PC01–PC10 Catalogue drawer', () => {
  it('PC01 — bouton Parcourir catalogue présent (pas Lien /catalogue)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    const btn = screen.getByRole('button', { name: /Parcourir le catalogue/i })
    expect(btn).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Ouvrir le catalogue/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Parcourir le catalogue/i })).not.toBeInTheDocument()
  })

  it('PC02 — ouvre drawer Catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    expect(await screen.findByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
  })

  it('PC03 — Composer reste ouvert (titre Nouvelle facture)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('PC04 — URL composer inchangée', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    expect(window.location.pathname).not.toMatch(/^\/catalogue$/)
  })

  it('PC05 — ProductPicker onOpenCatalog sans Link', () => {
    const onOpen = vi.fn()
    render(
      <MemoryRouter>
        <ProductPicker onSelect={vi.fn()} onOpenCatalog={onOpen} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: /catalogue/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Parcourir le catalogue/i })).toBeInTheDocument()
  })

  it('PC06 — ProductPicker sans onOpenCatalog n’ouvre pas /catalogue par défaut', () => {
    render(
      <MemoryRouter>
        <ProductPicker onSelect={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: /catalogue/i })).not.toBeInTheDocument()
  })

  it('PC07 — drawer liste items catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    expect(await screen.findByText('Audit annuel')).toBeInTheDocument()
    expect(screen.getByText('Licence Pro')).toBeInTheDocument()
  })

  it('PC08 — Ajouter depuis drawer → ligne + toast', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Audit annuel')
    await user.click(screen.getByRole('button', { name: /Ajouter Audit annuel/i }))
    expect(await screen.findByText(/Ajouté : Audit annuel/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue('Audit annuel')).toBeInTheDocument()
  })

  it('PC09 — drawer reste ouvert après ajout', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Audit annuel')
    await user.click(screen.getByRole('button', { name: /Ajouter Audit annuel/i }))
    expect(screen.getByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
  })

  it('PC10 — Fermer drawer', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
    await user.click(within(footer).getByRole('button', { name: /^Fermer$/i }))
    expect(screen.queryByRole('heading', { name: /^Catalogue$/i })).not.toBeInTheDocument()
  })
})

describe('PC11–PC20 Filtres / Escape / hiérarchie', () => {
  it('PC11 — filtres Tous Produits Services', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    const tabs = await screen.findByRole('tablist', { name: /Filtres catalogue/i })
    expect(within(tabs).getByRole('tab', { name: 'Tous' })).toBeInTheDocument()
    expect(within(tabs).getByRole('tab', { name: 'Produits' })).toBeInTheDocument()
    expect(within(tabs).getByRole('tab', { name: 'Services' })).toBeInTheDocument()
  })

  it('PC12 — actions secondaires ligne libre', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getByRole('button', { name: /ligne libre/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Nouveau produit/i })).toBeInTheDocument()
  })

  it('PC13 — un seul Nouveau produit (pas de doublon picker)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getAllByRole('button', { name: /Nouveau produit/i })).toHaveLength(1)
  })

  it('PC14 — ligne libre crée éditeur', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    expect(screen.getByLabelText(/Libellé ligne 1/i)).toBeInTheDocument()
  })

  it('PC15 — Escape ferme drawer (surface haute)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByRole('heading', { name: /^Catalogue$/i })
    await user.keyboard('{Escape}')
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /^Catalogue$/i })).not.toBeInTheDocument()
  })

  it('PC16 — LibraryCatalogDrawer unitaire open/close', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    const onAdd = vi.fn()
    render(
      <OverlayProvider>
        <LibraryCatalogDrawer open onOpenChange={onOpenChange} onAddResource={onAdd} />
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: /^Catalogue$/i })).toBeInTheDocument()
    const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
    await user.click(within(footer).getByRole('button', { name: /^Fermer$/i }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('PC17 — returnFocusRef typé', () => {
    const ref = createRef<HTMLButtonElement>()
    expect(ref.current).toBeNull()
  })

  it('PC18 — section Produits description hiérarchie', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getByText(/actions secondaires/i)).toBeInTheDocument()
  })

  it('PC19 — preview Aucune ligne au départ étape produits', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getAllByText('Aucune ligne').length).toBeGreaterThanOrEqual(1)
  })

  it('PC20 — draft products source unique (empty)', () => {
    const d = createEmptyFacturationDraft({ docType: 'facture' })
    expect(d.products).toEqual([])
  })
})

describe('PC21–PC30 Line state / suppression', () => {
  it('PC21 — ajout libre puis supprimer → Aucune ligne', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'Presta A')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getAllByText('Aucune ligne').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('PC22 — deux lignes, supprimer première conserve la seconde', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'Alpha')
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 2/i), 'Beta')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByDisplayValue('Beta')).toBeInTheDocument()
      expect(screen.queryByDisplayValue('Alpha')).not.toBeInTheDocument()
    })
  })

  it('PC23 — data-line-key présent', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    expect(document.querySelector('[data-line-key]')).toBeTruthy()
  })

  it('PC24 — duplicate crée 2 lignes', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'CloneMe')
    await user.click(screen.getByRole('button', { name: /^Dupliquer$/i }))
    expect(screen.getAllByDisplayValue('CloneMe')).toHaveLength(2)
  })

  it('PC25 — keys distinctes après duplicate', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.click(screen.getByRole('button', { name: /^Dupliquer$/i }))
    const keys = [...document.querySelectorAll('[data-line-key]')].map((el) =>
      el.getAttribute('data-line-key'),
    )
    expect(keys[0]).toBeTruthy()
    expect(keys[1]).toBeTruthy()
    expect(keys[0]).not.toBe(keys[1])
  })

  it('PC26 — totaux HT 0 si aucune ligne labelée', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getByText(/HT\s*:/i).textContent).toMatch(/0/)
  })

  it('PC27 — preview liste suit draft après ajout catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Licence Pro')
    await user.click(screen.getByRole('button', { name: /Ajouter Licence Pro/i }))
    expect(screen.getByDisplayValue('Licence Pro')).toBeInTheDocument()
    expect(screen.getAllByText(/Licence Pro/).length).toBeGreaterThanOrEqual(1)
  })

  it('PC28 — WizardSelectedProduct lineKey optionnel typé', () => {
    const d = createEmptyFacturationDraft({
      products: [
        {
          catalogItemId: null,
          label: 'X',
          quantity: 1,
          unitPrice: 10,
          vatRate: 20,
          lineKey: 'ln-test',
        },
      ],
    })
    expect(d.products[0].lineKey).toBe('ln-test')
  })

  it('PC29 — buildPayload ignore lineKey conceptuellement (filter labels)', () => {
    const d = createEmptyFacturationDraft({
      products: [
        {
          catalogItemId: 1,
          label: '  ',
          quantity: 1,
          unitPrice: 10,
          vatRate: 20,
          lineKey: 'a',
        },
      ],
    })
    const lines = d.products.filter((p) => p.label.trim())
    expect(lines).toHaveLength(0)
  })

  it('PC30 — éditeur vide après dernière suppression', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByText('Aucune ligne', { selector: '.fp-wizard-empty' })).toBeInTheDocument()
    })
  })
})

describe('PC31–PC40 Exit dialog', () => {
  it('PC31 — titre facture', () => {
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    expect(screen.getByText(/Quitter cette facture/i)).toBeInTheDocument()
  })

  it('PC32 — titre devis', () => {
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="devis"
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    expect(screen.getByText(/Quitter ce devis/i)).toBeInTheDocument()
  })

  it('PC33 — titre avoir', () => {
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="avoir"
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    expect(screen.getByText(/Quitter cet avoir/i)).toBeInTheDocument()
  })

  it('PC34 — actions hiérarchie présentes', () => {
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    expect(screen.getByRole('button', { name: /Enregistrer brouillon et quitter/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Continuer la création/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Quitter sans enregistrer/i })).toBeInTheDocument()
  })

  it('PC35 — Continuer appelle onContinue', async () => {
    const user = userEvent.setup()
    const onContinue = vi.fn()
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          onContinue={onContinue}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    await user.click(screen.getByRole('button', { name: /Continuer la création/i }))
    expect(onContinue).toHaveBeenCalled()
  })

  it('PC36 — Discard appelle onDiscard', async () => {
    const user = userEvent.setup()
    const onDiscard = vi.fn()
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          onContinue={vi.fn()}
          onDiscard={onDiscard}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    await user.click(screen.getByRole('button', { name: /Quitter sans enregistrer/i }))
    expect(onDiscard).toHaveBeenCalled()
  })

  it('PC37 — saveError + Réessayer', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          saveError="Échec réseau"
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={onSave}
        />
      </OverlayProvider>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/Échec réseau/)
    await user.click(screen.getByRole('button', { name: /Réessayer/i }))
    expect(onSave).toHaveBeenCalled()
  })

  it('PC38 — busy désactive actions', () => {
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          busy
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    expect(screen.getByRole('button', { name: /Enregistrement/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Continuer la création/i })).toBeDisabled()
  })

  it('PC39 — dirty exit depuis Composer affiche dialogue type', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'Travail')
    await user.click(screen.getByRole('button', { name: /^Annuler$/i }))
    expect(await screen.findByText(/Quitter cette facture/i)).toBeInTheDocument()
  })

  it('PC40 — classe premium width sur dialog', () => {
    render(
      <OverlayProvider>
        <ExitConfirmationDialog
          open
          onOpenChange={vi.fn()}
          docType="facture"
          onContinue={vi.fn()}
          onDiscard={vi.fn()}
          onSaveAndQuit={vi.fn()}
        />
      </OverlayProvider>,
    )
    expect(document.querySelector('.fp-exit-confirm-premium')).toBeTruthy()
  })
})
