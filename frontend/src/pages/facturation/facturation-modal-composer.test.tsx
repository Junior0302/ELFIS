/**
 * F1.3.1.2 — Modal Composer Full Workflow (MC01–MC40)
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { ComposerDialog } from '../../comptapilot/facturation/ComposerDialog'
import { DocumentCreateFlow } from '../../comptapilot/facturation/DocumentCreateFlow'
import { OverlayProvider, OverlayRouteBridge } from '../../design-system/overlays'
import {
  isComposerFullFocusPath,
  isComposerModalPath,
} from '../../components/layouts/WorkspaceLayout'
import { ComposerFocusLayout, type ComposerDefinition, type ComposerStepDefinition } from '../../composer-framework'
import type { BillingOverview } from '../../api'
import { createRef, useState } from 'react'
import FacturationDocumentsPage from './FacturationDocumentsPage'
import FacturationNouveauRedirect from './FacturationNouveauRedirect'
import FacturationComposerPage from './FacturationComposerPage'

const billingOverviewMock = vi.fn()

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
      listCatalog: vi.fn().mockResolvedValue({ items: [] }),
      createCustomer: vi.fn().mockResolvedValue({
        id: 99,
        name: 'Client Test',
        email: 'client@test.example',
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

const STEPS: ComposerStepDefinition[] = [
  { id: 'client', label: 'Client' },
  { id: 'lines', label: 'Lignes' },
]

function focusDef(): ComposerDefinition {
  return {
    id: 'mc-test',
    title: 'Nouvelle facture',
    documentType: 'Facture',
    statusLabel: 'Brouillon',
    steps: STEPS,
    currentStepId: 'client',
    stepStatuses: { client: 'current', lines: 'upcoming' },
  }
}

function renderDocs(path = '/facturation/documents') {
  return render(
    <OverlayProvider>
      <MemoryRouter initialEntries={[path]}>
        <OverlayRouteBridge />
        <Routes>
          <Route path="/facturation" element={<FacturationLayout />}>
            <Route path="documents" element={<FacturationDocumentsPage />}>
              <Route path="new" element={null} />
            </Route>
            <Route path="nouveau" element={<FacturationNouveauRedirect />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </OverlayProvider>,
  )
}

beforeEach(() => {
  cleanup()
  billingOverviewMock.mockResolvedValue(sampleOverview())
})

afterEach(() => cleanup())

describe('MC01–MC10 Audit / routing', () => {
  it('MC01 — isComposerFullFocusPath toujours false (plus de page Focus)', () => {
    expect(isComposerFullFocusPath('/facturation/nouveau')).toBe(false)
    expect(isComposerFullFocusPath('/facturation/documents/new')).toBe(false)
  })

  it('MC02 — isComposerModalPath détecte /documents/new', () => {
    expect(isComposerModalPath('/facturation/documents/new')).toBe(true)
    expect(isComposerModalPath('/facturation/documents')).toBe(false)
  })

  it('MC03 — Documents reste monté sous /documents/new', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
  })

  it('MC04 — deep link /nouveau redirige vers documents/new', async () => {
    renderDocs('/facturation/nouveau?type=devis')
    expect(await screen.findByRole('heading', { name: 'Nouveau devis' })).toBeInTheDocument()
  })

  it('MC05 — /documents/new sans type → pop-in create', async () => {
    renderDocs('/facturation/documents/new')
    expect(await screen.findByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
  })

  it('MC06 — create=1 ouvre STATE 1 type', async () => {
    renderDocs('/facturation/documents?create=1')
    expect(await screen.findByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /devis/i })).toBeInTheDocument()
  })

  it('MC07 — nav Facturation visible derrière modal', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('navigation', { name: /espaces facturation/i })).toBeInTheDocument()
  })

  it('MC08 — ComposerDialog phase type size sm classes', () => {
    render(
      <OverlayProvider>
        <ComposerDialog open phase="type" onOpenChange={() => {}} title="Nouveau document">
          <p>type-body</p>
        </ComposerDialog>
      </OverlayProvider>,
    )
    const dlg = screen.getByRole('dialog')
    expect(dlg).toHaveClass('fp-create-flow--type')
    expect(screen.getByText('type-body')).toBeInTheDocument()
  })

  it('MC09 — ComposerDialog phase composer large', () => {
    render(
      <OverlayProvider>
        <ComposerDialog open phase="composer" onOpenChange={() => {}} aria-label="Création">
          <p>composer-body</p>
        </ComposerDialog>
      </OverlayProvider>,
    )
    const dlg = screen.getByRole('dialog', { name: /création de document/i })
    expect(dlg).toHaveClass('fp-create-flow--composer')
    expect(dlg).toHaveAttribute('data-fp-composer-dialog', 'true')
  })

  it('MC10 — Documents inert pendant ComposerDialog', () => {
    document.body.innerHTML = '<div data-billing-layout="fp05">docs</div>'
    render(
      <OverlayProvider>
        <ComposerDialog open phase="composer" onOpenChange={() => {}}>
          <span>x</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    const target = document.querySelector('[data-billing-layout="fp05"]')
    expect(target).toHaveAttribute('inert')
  })
})

describe('MC11–MC20 Flux type → composer', () => {
  it('MC11 — bouton Créer ouvre pop-in type', async () => {
    const user = userEvent.setup()
    renderDocs()
    await user.click(await screen.findByRole('button', { name: /créer un document/i }))
    expect(screen.getByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
  })

  it('MC12 — Créer le document désactivé sans type', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await screen.findByRole('heading', { name: 'Nouveau document' })
    expect(screen.getByRole('button', { name: /créer le document/i })).toBeDisabled()
    await user.click(screen.getByRole('radio', { name: /facture/i }))
    expect(screen.getByRole('button', { name: /créer le document/i })).not.toBeDisabled()
  })

  it('MC13 — type → composer sans page /nouveau', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await user.click(await screen.findByRole('radio', { name: /facture/i }))
    await user.click(screen.getByRole('button', { name: /créer le document/i }))
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
  })

  it('MC14 — radiogroup a11y type', async () => {
    renderDocs('/facturation/documents?create=1')
    await screen.findByRole('heading', { name: 'Nouveau document' })
    expect(screen.getByRole('radiogroup', { name: /type de document/i })).toBeInTheDocument()
  })

  it('MC15 — DocumentCreateFlow bridge phase composer', async () => {
    function Harness() {
      const [open, setOpen] = useState(true)
      const ref = createRef<HTMLButtonElement>()
      return (
        <OverlayProvider>
          <MemoryRouter initialEntries={['/facturation/documents']}>
            <Routes>
              <Route
                path="/facturation/documents"
                element={
                  <DocumentCreateFlow
                    typeOpen={open}
                    onTypeOpenChange={setOpen}
                    returnFocusRef={ref}
                  />
                }
              />
              <Route path="/facturation/documents/new" element={<div />} />
            </Routes>
          </MemoryRouter>
        </OverlayProvider>
      )
    }
    render(<Harness />)
    expect(await screen.findByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
  })

  it('MC16 — Composer modal presentation attr', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-fp-composer-presentation="modal"]')).toBeTruthy()
  })

  it('MC17 — ComposerFocusLayout dans dialog', async () => {
    renderDocs('/facturation/documents/new?type=avoir')
    await screen.findByRole('heading', { name: 'Nouvel avoir' })
    expect(document.querySelector('[data-composer-full-focus="true"]')).toBeTruthy()
  })

  it('MC18 — header retour Documents présent', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    expect(await screen.findByRole('button', { name: 'Documents' })).toBeInTheDocument()
  })

  it('MC19 — actions Annuler + footer Continuer (guidé)', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('button', { name: 'Annuler' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continuer' })).toBeInTheDocument()
  })

  it('MC20 — preview complementary landmark', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('complementary', { name: /aperçu document/i })).toBeInTheDocument()
  })
})

describe('MC21–MC30 Fermeture / dirty / confirm', () => {
  it('MC21 — exit vide ferme sans confirm', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: 'Documents' }))
    expect(screen.queryByText(/Quitter cette/i)).not.toBeInTheDocument()
  })

  it('MC22 — dirty ouvre confirm 3 actions', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
    await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Atelier')
    const createPanel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
    await user.click(within(createPanel).getByRole('button', { name: 'Enregistrer' }))
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    const confirm = await screen.findByRole('dialog', { name: /Quitter cette facture/i })
    expect(within(confirm).getByRole('button', { name: /Continuer la création/i })).toBeInTheDocument()
    expect(within(confirm).getByRole('button', { name: /Quitter sans enregistrer/i })).toBeInTheDocument()
    expect(within(confirm).getByRole('button', { name: /Enregistrer brouillon et quitter/i })).toBeInTheDocument()
  })

  it('MC23 — Continuer garde le composer', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
    await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Atelier')
    const createPanel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
    await user.click(within(createPanel).getByRole('button', { name: 'Enregistrer' }))
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    const confirm = await screen.findByRole('dialog', { name: /Quitter cette facture/i })
    await user.click(within(confirm).getByRole('button', { name: /Continuer la création/i }))
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('MC24 — page mode Composer toujours exportable', async () => {
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

  it('MC25 — confirmation layout actions', () => {
    render(
      <ComposerFocusLayout
        definition={focusDef()}
        confirmation={
          <div className="elf-cmp-focus__confirmation-actions">
            <button type="button">Ouvrir le document</button>
            <button type="button">Envoyer</button>
            <button type="button">Revenir aux Documents</button>
            <button type="button">Créer un autre</button>
          </div>
        }
      >
        x
      </ComposerFocusLayout>,
    )
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeInTheDocument()
  })

  it('MC26 — dialog role aria-modal composer', () => {
    render(
      <OverlayProvider>
        <ComposerDialog open phase="composer" onOpenChange={() => {}}>
          <span>c</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    const dlg = screen.getByRole('dialog')
    expect(dlg).toHaveAttribute('aria-modal', 'true')
  })

  it('MC27 — type dialog dismissible footer', () => {
    render(
      <OverlayProvider>
        <ComposerDialog
          open
          phase="type"
          onOpenChange={() => {}}
          title="Nouveau document"
          footer={<button type="button">Annuler</button>}
        >
          <span>t</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    expect(screen.getByRole('button', { name: 'Annuler' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fermer' })).toBeInTheDocument()
  })

  it('MC28 — phase data attribute backdrop', () => {
    render(
      <OverlayProvider>
        <ComposerDialog open phase="composer" onOpenChange={() => {}}>
          <span>c</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    expect(document.querySelector('[data-fp-create-phase="composer"]')).toBeTruthy()
  })

  it('MC29 — modal root class', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.fp-composer-modal-root')).toBeTruthy()
  })

  it('MC30 — elf-cmp-focus--modal class', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.elf-cmp-focus--modal')).toBeTruthy()
  })
})

describe('MC31–MC40 A11y / responsive markers / regress', () => {
  it('MC31 — CustomerPicker non auto-ouvert', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('MC32 — étape client guidée (pas freeform complet)', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('heading', { name: /Qui souhaitez-vous facturer/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter une ligne libre' })).not.toBeInTheDocument()
  })

  it('MC33 — export ComposerDialog module', async () => {
    const mod = await import('../../comptapilot/facturation/ComposerDialog')
    expect(mod.ComposerDialog).toBeTypeOf('function')
  })

  it('MC34 — export DocumentCreateFlow', async () => {
    const mod = await import('../../comptapilot/facturation/DocumentCreateFlow')
    expect(mod.DocumentCreateFlow).toBeTypeOf('function')
  })

  it('MC35 — Nouveau redirect module', async () => {
    const mod = await import('./FacturationNouveauRedirect')
    expect(mod.default).toBeTypeOf('function')
  })

  it('MC36 — small pop-in distinct du grand dialog', () => {
    const { rerender } = render(
      <OverlayProvider>
        <ComposerDialog open phase="type" onOpenChange={() => {}} title="T">
          <span>a</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toHaveClass('fp-create-flow--type')
    rerender(
      <OverlayProvider>
        <ComposerDialog open phase="composer" onOpenChange={() => {}}>
          <span>b</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toHaveClass('fp-create-flow--composer')
  })

  it('MC37 — filtres Documents toujours dans le DOM sous modal', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    // page Documents derrière
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
  })

  it('MC38 — exit confirm overlayType nested ok', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
    await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'X')
    const createPanel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
    await user.click(within(createPanel).getByRole('button', { name: 'Enregistrer' }))
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    const confirm = await screen.findByRole('dialog', { name: /Quitter cette facture/i })
    expect(within(confirm).getByRole('button', { name: /Quitter sans enregistrer/i })).toBeInTheDocument()
  })

  it('MC39 — workspace grid modal CSS class present', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.elf-cmp-focus__workspace')).toBeTruthy()
  })

  it('MC40 — pas de full-focus shell class sur spaces', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.fp-spaces--full-focus')).toBeNull()
  })
})
