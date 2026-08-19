/**
 * F1.3.2 — Guided Modal Composer GC01–GC40
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { OverlayProvider, OverlayRouteBridge } from '../../design-system/overlays'
import {
  COMPOSER_STEP_ORDER,
  validateComposerStep,
  createEmptyFacturationDraft,
} from '../../comptapilot/facturation/workflow'
import type { BillingOverview } from '../../api'
import FacturationDocumentsPage from './FacturationDocumentsPage'

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

async function addClient(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
  await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Dupont SAS')
  const panel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
  await user.click(within(panel).getByRole('button', { name: 'Enregistrer' }))
}

beforeEach(() => {
  cleanup()
  billingOverviewMock.mockResolvedValue(sampleOverview())
})

afterEach(() => cleanup())

describe('GC01–GC10 Machine / entrée guidée', () => {
  it('GC01 — 6 ComposerStep ordonnés', () => {
    expect(COMPOSER_STEP_ORDER).toHaveLength(6)
  })

  it('GC02 — modal démarre étape client', async () => {
    renderDocs()
    expect(await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })).toBeInTheDocument()
    expect(document.querySelector('[data-fp-guided-step="client"]')).toBeTruthy()
  })

  it('GC03 — data-fp-guided marker', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-fp-guided="1"]')).toBeTruthy()
  })

  it('GC04 — PDF / preview permanent à droite', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('complementary', { name: /aperçu document/i })).toBeInTheDocument()
  })

  it('GC05 — footer Retour désactivé sur client', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(screen.getByRole('button', { name: 'Retour' })).toBeDisabled()
  })

  it('GC06 — Continuer bloqué sans client (gate)', async () => {
    const user = userEvent.setup()
    renderDocs()
    await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/client/i)
    expect(document.querySelector('[data-fp-guided-step="client"]')).toBeTruthy()
  })

  it('GC07 — validateComposerStep items', () => {
    const d = createEmptyFacturationDraft({ docType: 'facture' })
    expect(validateComposerStep('items', d).ok).toBe(false)
  })

  it('GC08 — barre progression 6 labels', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('button', { name: 'Client' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Produits' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Finalisation' })).toBeInTheDocument()
  })

  it('GC09 — aria-current=step sur étape active', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(screen.getByRole('button', { name: 'Client' })).toHaveAttribute(
      'aria-current',
      'step',
    )
  })

  it('GC10 — Documents inert derrière', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-billing-layout="fp05"]')).toHaveAttribute('inert')
  })
})

describe('GC11–GC20 Navigation étapes', () => {
  it('GC11 — client → items après sélection', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(await screen.findByRole('heading', { name: /Quels produits et services/i })).toBeInTheDocument()
  })

  it('GC12 — items → gate sans ligne', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await screen.findByRole('heading', { name: /Quels produits et services/i })
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/ligne/i)
  })

  it('GC13 — items → terms avec ligne', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(await screen.findByRole('heading', { name: /Quelles conditions appliquer/i })).toBeInTheDocument()
    expect(document.querySelector('[data-fp-guided-step="terms"]')).toBeTruthy()
  })

  it('GC14 — Retour items → client', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await screen.findByRole('heading', { name: /Quels produits et services/i })
    await user.click(screen.getByRole('button', { name: 'Retour' }))
    expect(await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })).toBeInTheDocument()
  })

  it('GC15 — jump étape completed (Client) depuis items', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await screen.findByRole('heading', { name: /Quels produits et services/i })
    await user.click(screen.getByRole('button', { name: 'Client' }))
    expect(await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })).toBeInTheDocument()
  })

  it('GC16 — étape future Finalisation disabled', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(screen.getByRole('button', { name: 'Finalisation' })).toBeDisabled()
  })

  it('GC17 — terms → notes_payment', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await screen.findByRole('heading', { name: /Quelles conditions appliquer/i })
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(await screen.findByRole('heading', { name: /Notes et mentions/i })).toBeInTheDocument()
  })

  it('GC18 — notes_payment → review', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    expect(await screen.findByRole('heading', { name: /Tout est prêt à vérifier/i })).toBeInTheDocument()
  })

  it('GC19 — review → finalization', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    for (let i = 0; i < 4; i++) {
      await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    }
    expect(await screen.findByRole('heading', { name: /Finalisez votre document/i })).toBeInTheDocument()
  })

  it('GC20 — preview toujours monté après navigation', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(screen.getByRole('complementary', { name: /aperçu document/i })).toBeInTheDocument()
  })
})

describe('GC21–GC30 Contenu / a11y / layout', () => {
  it('GC21 — CustomerPicker non auto-ouvert', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('GC22 — guided class layout', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.elf-cmp-focus--guided')).toBeTruthy()
  })

  it('GC23 — workspace grid présent', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.elf-cmp-focus__workspace')).toBeTruthy()
  })

  it('GC24 — Annuler header présent', async () => {
    renderDocs()
    expect(await screen.findByRole('button', { name: 'Annuler' })).toBeInTheDocument()
  })

  it('GC25 — retour Documents', async () => {
    renderDocs()
    expect(await screen.findByRole('button', { name: 'Documents' })).toBeInTheDocument()
  })

  it('GC26 — progressbar track', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('GC27 — navigation progression landmark', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('navigation', { name: /progression/i })).toBeInTheDocument()
  })

  it('GC28 — step heading focusable', async () => {
    renderDocs()
    const h = await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(h).toHaveAttribute('tabIndex', '-1')
  })

  it('GC29 — pas de lignes sur étape client', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(screen.queryByRole('button', { name: 'Ajouter une ligne libre' })).not.toBeInTheDocument()
  })

  it('GC30 — modal root inchangé', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(
      document.querySelector('[data-fp-document-creation-modal-root="true"]'),
    ).toBeTruthy()
  })
})

describe('GC31–GC40 Finalization / regress', () => {
  it('GC31 — finalization actions enregistrer', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    for (let i = 0; i < 4; i++) {
      await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    }
    expect(
      await screen.findAllByRole('button', { name: /enregistrer le brouillon/i }),
    ).not.toHaveLength(0)
  })

  it('GC32 — review montre totaux', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    for (let i = 0; i < 3; i++) {
      await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    }
    await screen.findByRole('heading', { name: /Tout est prêt à vérifier/i })
    expect(screen.getByText(/^Totaux$/i)).toBeInTheDocument()
  })

  it('GC33 — notes étape', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Prestation')
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await user.click(await screen.findByRole('button', { name: 'Continuer' }))
    expect(await screen.findByLabelText(/Notes document/i)).toBeInTheDocument()
  })

  it('GC34 — export step machine', async () => {
    const mod = await import('../../comptapilot/facturation/workflow/composerStepMachine')
    expect(mod.validateComposerStep).toBeTypeOf('function')
  })

  it('GC35 — page mode freeform inchangé (non modal)', async () => {
    const { default: Page } = await import('./FacturationComposerPage')
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau?type=facture']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<Page />} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('heading', { name: /^Produits$/i })).toBeInTheDocument()
  })

  it('GC36 — exit vide sans confirm', async () => {
    const user = userEvent.setup()
    renderDocs()
    await user.click(await screen.findByRole('button', { name: 'Documents' }))
    expect(screen.queryByText(/Quitter cette/i)).not.toBeInTheDocument()
  })

  it('GC37 — overlay route ne casse pas guidé', async () => {
    renderDocs()
    expect(await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })).toBeInTheDocument()
  })

  it('GC38 — nav Facturation derrière', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('navigation', { name: /espaces facturation/i })).toBeInTheDocument()
  })

  it('GC39 — pas full-focus shell', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.fp-spaces--full-focus')).toBeNull()
  })

  it('GC40 — data-composer-step client', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-composer-step="client"]')).toBeTruthy()
  })
})

describe('DS01–DS08 Document Studio smoke UI', () => {
  it('DS01 — hero client présent', async () => {
    renderDocs()
    expect(
      await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i }),
    ).toBeInTheDocument()
    expect(document.querySelector('[data-ds-studio-hero="client"]')).toBeTruthy()
  })

  it('DS02 — marker studio', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[data-ds-studio="1"]')).toBeTruthy()
    expect(document.querySelector('.elf-cmp-focus--studio')).toBeTruthy()
  })

  it('DS03 — stepper current client', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(
      document.querySelector('[data-step-id="client"][data-step-status="current"]'),
    ).toBeTruthy()
    expect(
      document.querySelector('[data-step-id="items"][data-step-status="blocked"]'),
    ).toBeTruthy()
  })

  it('DS04 — PDF skeleton visible', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    expect(document.querySelector('[data-ds-pdf-skeleton="1"]')).toBeTruthy()
  })

  it('DS05 — PDF structure blocs', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    const pdf = document.querySelector('[data-ds-pdf-skeleton="1"]')
    expect(pdf?.querySelector('[data-ds-pdf-block="client"]')).toBeTruthy()
    expect(pdf?.querySelector('[data-ds-pdf-block="lines"]')).toBeTruthy()
    expect(pdf?.querySelector('[data-ds-pdf-block="totals"]')).toBeTruthy()
    expect(pdf?.querySelector('.ds-studio-pdf__footer')).toBeTruthy()
  })

  it('DS06 — smart card client + step completed', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    expect(document.querySelector('[data-ds-smart-card="client"]')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    await screen.findByRole('heading', { name: /Quels produits et services/i })
    expect(
      document.querySelector('[data-step-id="client"][data-step-status="completed"]'),
    ).toBeTruthy()
    expect(
      document.querySelector('[data-step-id="items"][data-step-status="current"]'),
    ).toBeTruthy()
  })

  it('DS07 — conseil placeholder + disclaimer', async () => {
    renderDocs()
    await screen.findByRole('heading', { name: /Qui souhaitez-vous facturer/i })
    const conseil = document.querySelector('[data-ds-conseil="placeholder"]')
    expect(conseil).toBeTruthy()
    expect(conseil?.textContent).toMatch(/moteur IA non connecté/i)
  })

  it('DS08 — products hero', async () => {
    const user = userEvent.setup()
    renderDocs()
    await addClient(user)
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(
      await screen.findByRole('heading', { name: /Quels produits et services/i }),
    ).toBeInTheDocument()
    expect(document.querySelector('[data-ds-studio-hero="items"]')).toBeTruthy()
  })
})
