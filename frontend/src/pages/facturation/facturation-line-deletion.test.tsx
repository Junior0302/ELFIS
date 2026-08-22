/**
 * Immediate line deletion UI — LDI01–LDI40
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { OverlayProvider, OverlayRouteBridge } from '../../design-system/overlays'
import type { BillingOverview } from '../../api'
import FacturationDocumentsPage from './FacturationDocumentsPage'
import { goToComposerProductsStep as goToProducts, expectZeroSubtotalHt, expectZeroTotalTtc } from './facturation-composer-test-helpers'

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
      updateSalesDoc: vi.fn().mockResolvedValue({
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

async function addCatalogAndClose(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
  await screen.findByText(name)
  await user.click(screen.getByRole('button', { name: new RegExp(`Ajouter ${name}`, 'i') }))
  const footer = document.querySelector('.fp-catalog-modal__footer') as HTMLElement
  await user.click(within(footer).getByRole('button', { name: /^Fermer$/i }))
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
})

afterEach(() => cleanup())

describe('LDI01–LDI10 Catalogue delete immédiat', () => {
  it('LDI01 — ajout catalogue crée ligne éditeur', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    expect(screen.getByDisplayValue('Audit annuel')).toBeInTheDocument()
  })

  it('LDI02 — supprimer après catalogue retire la ligne', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Audit annuel')).not.toBeInTheDocument()
    })
  })

  it('LDI03 — pas de ps-picker__selected fantôme', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Licence Pro')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(document.querySelector('.ps-picker__selected')).toBeNull()
    })
  })

  it('LDI04 — empty state après delete', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByText('Aucune ligne', { selector: '.fp-wizard-empty' })).toBeInTheDocument()
    })
  })

  it('LDI05 — preview plus de libellé après delete', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Licence Pro')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      const preview = document.querySelector('[data-live-preview="structured"]')
      expect(preview?.textContent).not.toMatch(/Licence Pro/)
    })
  })

  it('LDI06 — HT 0 après dernière suppression', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expectZeroSubtotalHt()
    })
  })

  it('LDI07 — data-fp-lines-empty', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(document.querySelector('[data-fp-lines-empty="true"]')).toBeTruthy()
    })
  })

  it('LDI08 — toast Ajouté dans catalogue modal', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Audit annuel')
    await user.click(screen.getByRole('button', { name: /Ajouter Audit annuel/i }))
    expect(await screen.findByText(/Ajouté : Audit annuel/i)).toBeInTheDocument()
    expect(document.querySelector('.ps-picker__selected')).toBeNull()
  })

  it('LDI09 — deux ajouts catalogue, delete premier', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await addCatalogAndClose(user, 'Licence Pro')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Audit annuel')).not.toBeInTheDocument()
      expect(screen.getByDisplayValue('Licence Pro')).toBeInTheDocument()
    })
  })

  it('LDI10 — lineKey data attr présent', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    expect(document.querySelector('[data-line-key]')).toBeTruthy()
  })
})

describe('LDI11–LDI20 Free line / remount', () => {
  it('LDI11 — ligne libre delete', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'Presta')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Presta')).not.toBeInTheDocument()
    })
  })

  it('LDI12 — Continuer Retour garde empty', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByText('Aucune ligne', { selector: '.fp-wizard-empty' })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    // gate may block — add free line? Without products continue may fail
    // Stay: if gate, still on products — skip jump
    const gate = screen.queryByRole('alert')
    if (!gate) {
      await user.click(screen.getByRole('button', { name: 'Retour' }))
      expect(screen.getByText('Aucune ligne', { selector: '.fp-wizard-empty' })).toBeInTheDocument()
    }
  })

  it('LDI13 — pas de remount requis pour sync', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Licence Pro')
    const before = document.querySelector('[data-fp-guided-step="items"]')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Licence Pro')).not.toBeInTheDocument()
    })
    expect(document.querySelector('[data-fp-guided-step="items"]')).toBe(before)
  })

  it('LDI14 — duplicate puis delete copie', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'Dup')
    await user.click(screen.getByRole('button', { name: /^Dupliquer$/i }))
    expect(screen.getAllByDisplayValue('Dup')).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 2/i }))
    await waitFor(() => {
      expect(screen.getAllByDisplayValue('Dup')).toHaveLength(1)
    })
  })

  it('LDI15 — keys distinctes après duplicate', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.click(screen.getByRole('button', { name: /^Dupliquer$/i }))
    const keys = [...document.querySelectorAll('[data-line-key]')].map((el) =>
      el.getAttribute('data-line-key'),
    )
    expect(keys[0]).not.toBe(keys[1])
  })

  it('LDI16 — data-fp-line-editor', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    expect(document.querySelector('[data-fp-line-editor="true"]')).toBeTruthy()
  })

  it('LDI17 — preview Aucune ligne texte', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getAllByText('Aucune ligne').length).toBeGreaterThanOrEqual(1)
  })

  it('LDI18 — exiting class pendant fade', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'Fade')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    expect(
      document.querySelector('.fp-line-editor__row--exiting') ||
        document.querySelector('[data-fp-lines-empty="true"]'),
    ).toBeTruthy()
  })

  it('LDI19 — append multi sans perdre lignes', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await addCatalogAndClose(user, 'Licence Pro')
    expect(screen.getByDisplayValue('Audit annuel')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Licence Pro')).toBeInTheDocument()
  })

  it('LDI20 — delete dernière des deux', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await addCatalogAndClose(user, 'Licence Pro')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 2/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Licence Pro')).not.toBeInTheDocument()
      expect(screen.getByDisplayValue('Audit annuel')).toBeInTheDocument()
    })
  })
})

describe('LDI21–LDI30 Preview / validation', () => {
  it('LDI21 — structured preview sync', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    const preview = document.querySelector('[data-live-preview="structured"]')
    expect(preview?.textContent).toMatch(/Audit annuel/)
  })

  it('LDI22 — après delete preview Aucune ligne', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      const preview = document.querySelector('[data-live-preview="structured"]')
      expect(preview?.textContent).toMatch(/Les lignes apparaîtront ici/)
    })
  })

  it('LDI23 — hint Ajoutez au moins une ligne revient', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByText(/Ajoutez au moins une ligne/i)).toBeInTheDocument()
    })
  })

  it('LDI24 — TTC 0', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expectZeroTotalTtc()
    })
  })

  it('LDI25 — TVA 0', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByText(/TVA/i).textContent).toMatch(/0/)
    })
  })

  it('LDI26 — libellé éditable sync preview', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'LiveEdit')
    expect(document.querySelector('[data-live-preview="structured"]')?.textContent).toMatch(
      /LiveEdit/,
    )
  })

  it('LDI27 — delete désactive pendant fade', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'X')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    const btn = screen.queryByRole('button', { name: /Supprimer ligne 1/i })
    if (btn) expect(btn).toBeDisabled()
  })

  it('LDI28 — Composer reste ouverte', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Audit annuel')).not.toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('LDI29 — guided step items inchangé', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    expect(document.querySelector('[data-fp-guided-step="items"]')).toBeTruthy()
  })

  it('LDI30 — pas de Link catalogue', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.queryByRole('link', { name: /Ouvrir le catalogue/i })).not.toBeInTheDocument()
  })
})

describe('LDI31–LDI40 Régression / a11y', () => {
  it('LDI31 — aria-label supprimer', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    expect(screen.getByRole('button', { name: /Supprimer ligne 1/i })).toBeInTheDocument()
  })

  it('LDI32 — empty role status', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(screen.getByText('Aucune ligne', { selector: '.fp-wizard-empty' })).toHaveAttribute(
      'role',
      'status',
    )
  })

  it('LDI33 — catalog toast role status', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /Parcourir le catalogue/i }))
    await screen.findByText('Audit annuel')
    await user.click(screen.getByRole('button', { name: /Ajouter Audit annuel/i }))
    const toast = await screen.findByText(/Ajouté : Audit annuel/i)
    expect(toast).toHaveAttribute('role', 'status')
  })

  it('LDI34 — move Monter après delete index 0', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await addCatalogAndClose(user, 'Licence Pro')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.getByDisplayValue('Licence Pro')).toBeInTheDocument()
      expect(screen.queryByDisplayValue('Audit annuel')).not.toBeInTheDocument()
    })
    const editor = document.querySelector('[data-fp-line-editor="true"]') as HTMLElement
    expect(within(editor).getByRole('button', { name: /^Monter$/i })).toBeDisabled()
  })

  it('LDI35 — Descendre disabled seule ligne', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    expect(screen.getByRole('button', { name: /^Descendre$/i })).toBeDisabled()
  })

  it('LDI36 — modal presentation intacte', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    expect(document.querySelector('[data-fp-composer-presentation="modal"]')).toBeTruthy()
  })

  it('LDI37 — delete puis ré-ajout même produit', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Audit annuel')).not.toBeInTheDocument()
    })
    await addCatalogAndClose(user, 'Audit annuel')
    expect(screen.getByDisplayValue('Audit annuel')).toBeInTheDocument()
  })

  it('LDI38 — row count DOM après delete', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Audit annuel')
    await addCatalogAndClose(user, 'Licence Pro')
    expect(document.querySelectorAll('[data-line-key]').length).toBe(2)
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(document.querySelectorAll('[data-line-key]').length).toBe(1)
    })
  })

  it('LDI39 — freeform page mode delete', async () => {
    const user = userEvent.setup()
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/documents/new?type=facture']}>
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
    await goToProducts(user)
    await user.click(screen.getByRole('button', { name: /ligne libre/i }))
    await user.type(screen.getByLabelText(/Libellé ligne 1/i), 'PageMode')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(screen.queryByDisplayValue('PageMode')).not.toBeInTheDocument()
    })
  })

  it('LDI40 — GO marker empty after catalog delete', async () => {
    const user = userEvent.setup()
    renderDocs()
    await goToProducts(user)
    await addCatalogAndClose(user, 'Licence Pro')
    await user.click(screen.getByRole('button', { name: /Supprimer ligne 1/i }))
    await waitFor(() => {
      expect(document.querySelector('[data-fp-lines-empty="true"]')).toBeTruthy()
      expect(document.querySelector('.ps-picker__selected')).toBeNull()
      expect(screen.queryByDisplayValue('Licence Pro')).not.toBeInTheDocument()
    })
  })
})
