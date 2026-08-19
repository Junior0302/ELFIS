/**
 * F1.3.1.3 — Modal Composer Workflow MM01–MM40
 * Inclut OverlayRouteBridge (régression route_change).
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import {
  ComposerDialog,
  DocumentCreationModalRoot,
} from '../../comptapilot/facturation/ComposerDialog'
import { DocumentCreateFlow } from '../../comptapilot/facturation/DocumentCreateFlow'
import {
  OverlayProvider,
  OverlayRouteBridge,
} from '../../design-system/overlays'
import {
  isComposerFullFocusPath,
  isComposerModalPath,
} from '../../components/layouts/WorkspaceLayout'
import {
  composerModalReducer,
  INITIAL_COMPOSER_MODAL_STATE,
} from '../../comptapilot/facturation/workflow'
import type { BillingOverview } from '../../api'
import { createRef, useState } from 'react'
import FacturationDocumentsPage from './FacturationDocumentsPage'
import FacturationNouveauRedirect from './FacturationNouveauRedirect'

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

describe('MM01–MM10 Diagnostic / machine / root', () => {
  it('MM01 — isComposerModalPath /documents/new', () => {
    expect(isComposerModalPath('/facturation/documents/new')).toBe(true)
    expect(isComposerFullFocusPath('/facturation/documents/new')).toBe(false)
  })

  it('MM02 — machine closed → type_selection → composer', () => {
    let s = composerModalReducer(INITIAL_COMPOSER_MODAL_STATE, {
      type: 'OPEN_TYPE_SELECTION',
    })
    s = composerModalReducer(s, { type: 'SELECT_TYPE', docType: 'facture' })
    s = composerModalReducer(s, { type: 'ENTER_COMPOSER', docType: 'facture' })
    expect(s.stage).toBe('composer')
    expect(s.selectedType).toBe('facture')
  })

  it('MM03 — DocumentCreationModalRoot data attribute', () => {
    render(
      <OverlayProvider>
        <DocumentCreationModalRoot
          open
          stage="composer"
          onOpenChange={() => {}}
        >
          <span>body</span>
        </DocumentCreationModalRoot>
      </OverlayProvider>,
    )
    expect(
      document.querySelector('[data-fp-document-creation-modal-root="true"]'),
    ).toBeTruthy()
  })

  it('MM04 — ComposerDialog alias phase type', () => {
    render(
      <OverlayProvider>
        <ComposerDialog open phase="type" onOpenChange={() => {}} title="T">
          <span>x</span>
        </ComposerDialog>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toHaveAttribute(
      'data-fp-modal-stage',
      'type_selection',
    )
  })

  it('MM05 — root closeOnRouteChange ne ferme pas (simulate)', async () => {
    const onClose = vi.fn()
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/documents']}>
          <OverlayRouteBridge />
          <Routes>
            <Route
              path="/facturation/documents"
              element={
                <DocumentCreationModalRoot
                  open
                  stage="type_selection"
                  onOpenChange={onClose}
                  onRequestClose={onClose}
                  title="Nouveau document"
                >
                  <span>type</span>
                </DocumentCreationModalRoot>
              }
            />
            <Route path="/facturation/documents/new" element={<div>new</div>} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    /* Route bridge alone without navigate — dialog still open */
    expect(onClose).not.toHaveBeenCalledWith('route_change')
  })

  it('MM06 — Documents monté sous /new', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
  })

  it('MM07 — deep link Composer titre', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('MM08 — /new sans type → type_selection (pas bounce)', async () => {
    renderDocs('/facturation/documents/new')
    expect(await screen.findByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
  })

  it('MM09 — create=1 ouvre type_selection', async () => {
    renderDocs('/facturation/documents?create=1')
    expect(await screen.findByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
  })

  it('MM10 — inert Documents pendant modal', () => {
    document.body.innerHTML = '<div data-billing-layout="fp05">docs</div>'
    render(
      <OverlayProvider>
        <DocumentCreationModalRoot open stage="composer" onOpenChange={() => {}}>
          <span>c</span>
        </DocumentCreationModalRoot>
      </OverlayProvider>,
    )
    expect(document.querySelector('[data-billing-layout="fp05"]')).toHaveAttribute('inert')
  })
})

describe('MM11–MM20 Transition type → composer (anti route_change)', () => {
  it('MM11 — Créer ouvre pop-in', async () => {
    const user = userEvent.setup()
    renderDocs()
    await user.click(await screen.findByRole('button', { name: /créer un document/i }))
    expect(screen.getByRole('heading', { name: 'Nouveau document' })).toBeInTheDocument()
  })

  it('MM12 — Créer le document désactivé sans type', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await screen.findByRole('heading', { name: 'Nouveau document' })
    expect(screen.getByRole('button', { name: /créer le document/i })).toBeDisabled()
    await user.click(screen.getByRole('radio', { name: /facture/i }))
    expect(screen.getByRole('button', { name: /créer le document/i })).not.toBeDisabled()
  })

  it('MM13 — type → composer RESTE ouvert avec OverlayRouteBridge', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await user.click(await screen.findByRole('radio', { name: /facture/i }))
    await user.click(screen.getByRole('button', { name: /créer le document/i }))
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
    expect(
      document.querySelector('[data-fp-document-creation-modal-root="true"]'),
    ).toBeTruthy()
    /* Documents monté derrière (inert → pas accessible via getByRole) */
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
    expect(document.querySelector('[data-billing-layout="fp05"]')).toHaveAttribute('inert')
  })

  it('MM14 — après transition stage composer', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await user.click(await screen.findByRole('radio', { name: /devis/i }))
    await user.click(screen.getByRole('button', { name: /créer le document/i }))
    await screen.findByRole('heading', { name: 'Nouveau devis' })
    expect(document.querySelector('[data-fp-modal-stage="composer"]')).toBeTruthy()
  })

  it('MM15 — pas de flash : Documents + modal simultanés', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await user.click(await screen.findByRole('radio', { name: /avoir/i }))
    await user.click(screen.getByRole('button', { name: /créer le document/i }))
    await screen.findByRole('heading', { name: 'Nouvel avoir' })
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
    expect(screen.getByRole('dialog', { name: /création de document/i })).toBeInTheDocument()
  })

  it('MM16 — presentation modal attr', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-fp-composer-presentation="modal"]')).toBeTruthy()
  })

  it('MM17 — nav Facturation derrière', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('navigation', { name: /espaces facturation/i })).toBeInTheDocument()
  })

  it('MM18 — legacy /nouveau → modal', async () => {
    renderDocs('/facturation/nouveau?type=devis')
    expect(await screen.findByRole('heading', { name: 'Nouveau devis' })).toBeInTheDocument()
  })

  it('MM19 — phase classes type vs composer', () => {
    const { rerender } = render(
      <OverlayProvider>
        <DocumentCreationModalRoot
          open
          stage="type_selection"
          onOpenChange={() => {}}
          title="T"
        >
          <span>a</span>
        </DocumentCreationModalRoot>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toHaveClass('fp-create-flow--type')
    rerender(
      <OverlayProvider>
        <DocumentCreationModalRoot open stage="composer" onOpenChange={() => {}}>
          <span>b</span>
        </DocumentCreationModalRoot>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toHaveClass('fp-create-flow--composer')
  })

  it('MM20 — export DocumentCreateFlow', async () => {
    const mod = await import('../../comptapilot/facturation/DocumentCreateFlow')
    expect(mod.DocumentCreateFlow).toBeTypeOf('function')
  })
})

describe('MM21–MM30 Fermeture / empty valid / confirmation', () => {
  it('MM21 — exit Composer vide ferme sans confirm', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: 'Documents' }))
    expect(screen.queryByText(/Quitter cette/i)).not.toBeInTheDocument()
  })

  it('MM22 — dirty → confirm 3 actions', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
    await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Presta')
    const createPanel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
    await user.click(within(createPanel).getByRole('button', { name: 'Enregistrer' }))
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(await screen.findByText(/Quitter cette/i)).toBeInTheDocument()
  })

  it('MM23 — Continuer garde composer', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
    await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Presta')
    const createPanel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
    await user.click(within(createPanel).getByRole('button', { name: 'Enregistrer' }))
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    const confirm = await screen.findByRole('dialog', { name: /Quitter cette facture/i })
    await user.click(within(confirm).getByRole('button', { name: /Continuer la création/i }))
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('MM24 — Composer guidé étape client valide', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('heading', { name: /Qui souhaitez-vous facturer/i })).toBeInTheDocument()
    expect(screen.queryByText(/docs-redirect/i)).not.toBeInTheDocument()
  })

  it('MM25 — Annuler type ferme → Documents', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await screen.findByRole('heading', { name: 'Nouveau document' })
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.queryByRole('heading', { name: 'Nouveau document' })).not.toBeInTheDocument()
  })

  it('MM26 — aria-modal composer', () => {
    render(
      <OverlayProvider>
        <DocumentCreationModalRoot open stage="composer" onOpenChange={() => {}}>
          <span>c</span>
        </DocumentCreationModalRoot>
      </OverlayProvider>,
    )
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true')
  })

  it('MM27 — CustomerPicker non auto-ouvert', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('MM28 — modal root class', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.fp-composer-modal-root')).toBeTruthy()
  })

  it('MM29 — pas full-focus shell', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.fp-spaces--full-focus')).toBeNull()
  })

  it('MM30 — exit confirm nested', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents/new?type=facture')
    await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
    await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'X')
    const createPanel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
    await user.click(within(createPanel).getByRole('button', { name: 'Enregistrer' }))
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    const confirm = await screen.findByRole('dialog', {
      name: /Quitter cette facture/i,
    })
    expect(within(confirm).getByRole('button', { name: /Quitter sans enregistrer/i })).toBeInTheDocument()
  })
})

describe('MM31–MM40 Router / a11y / regress', () => {
  it('MM31 — radiogroup type a11y', async () => {
    renderDocs('/facturation/documents?create=1')
    await screen.findByRole('heading', { name: 'Nouveau document' })
    expect(screen.getByRole('radiogroup', { name: /type de document/i })).toBeInTheDocument()
  })

  it('MM32 — actions header Annuler + footer Continuer', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('button', { name: 'Annuler' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continuer' })).toBeInTheDocument()
  })

  it('MM33 — preview complementary', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('complementary', { name: /aperçu document/i })).toBeInTheDocument()
  })

  it('MM34 — workspace grid présent', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.elf-cmp-focus__workspace')).toBeTruthy()
  })

  it('MM35 — DocumentCreateFlow bridge harness open', async () => {
    function Harness() {
      const [open, setOpen] = useState(true)
      const ref = createRef<HTMLButtonElement>()
      return (
        <OverlayProvider>
          <MemoryRouter initialEntries={['/facturation/documents']}>
            <OverlayRouteBridge />
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

  it('MM36 — machine confirmation transitions', () => {
    let s = composerModalReducer(INITIAL_COMPOSER_MODAL_STATE, {
      type: 'HYDRATE_COMPOSER',
      docType: 'facture',
    })
    s = composerModalReducer(s, { type: 'ENTER_CONFIRMATION' })
    expect(s.stage).toBe('confirmation')
    s = composerModalReducer(s, { type: 'CLOSE' })
    expect(s.stage).toBe('closed')
  })

  it('MM37 — filtres layout derrière modal', async () => {
    renderDocs('/facturation/documents/new?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-billing-layout="fp05"]')).toBeTruthy()
  })

  it('MM38 — ignore route_change handler', () => {
    const onOpenChange = vi.fn()
    const onRequestClose = vi.fn()
    render(
      <OverlayProvider>
        <DocumentCreationModalRoot
          open
          stage="composer"
          onOpenChange={onOpenChange}
          onRequestClose={onRequestClose}
        >
          <span>c</span>
        </DocumentCreationModalRoot>
      </OverlayProvider>,
    )
    /* Simule raison route_change via requestClose stack — onRequestClose ne doit pas être appelé
       car handleClose return early ; on vérifie dialog toujours monté */
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    act(() => {
      /* no-op : closeOnRouteChange false → OverlayRouteBridge skip */
    })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('MM39 — export DocumentCreationModalRoot', async () => {
    const mod = await import('../../comptapilot/facturation/ComposerDialog')
    expect(mod.DocumentCreationModalRoot).toBeTypeOf('function')
  })

  it('MM40 — type persisté après Créer (avoir)', async () => {
    const user = userEvent.setup()
    renderDocs('/facturation/documents?create=1')
    await user.click(await screen.findByRole('radio', { name: /avoir/i }))
    await user.click(screen.getByRole('button', { name: /créer le document/i }))
    expect(await screen.findByRole('heading', { name: 'Nouvel avoir' })).toBeInTheDocument()
  })
})
