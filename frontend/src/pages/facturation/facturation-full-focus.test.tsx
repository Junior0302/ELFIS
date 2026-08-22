/**
 * F1.3.1.1 — Full Focus Mode Composer (FF01–FF40)
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'
import { OverlayProvider } from '../../design-system/overlays'
import {
  ComposerFocusLayout,
  useComposerFocus,
  type ComposerDefinition,
  type ComposerStepDefinition,
} from '../../composer-framework'
import { isComposerFullFocusPath, isComposerModalPath } from '../../components/layouts/WorkspaceLayout'

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
      listSharedRelations: vi.fn().mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      }),
      listCustomers: vi.fn().mockResolvedValue({ customers: [] }),
      listCatalog: vi.fn().mockResolvedValue({ items: [] }),
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

import FacturationComposerPage from './FacturationComposerPage'

const STEPS: ComposerStepDefinition[] = [
  { id: 'client', label: 'Client' },
  { id: 'lines', label: 'Lignes' },
]

function focusDef(over: Partial<ComposerDefinition> = {}): ComposerDefinition {
  return {
    id: 'ff-test',
    title: 'Nouvelle facture',
    documentType: 'Facture',
    statusLabel: 'Brouillon',
    steps: STEPS,
    currentStepId: 'client',
    stepStatuses: { client: 'current', lines: 'upcoming' },
    ...over,
  }
}

function renderComposer(path = '/facturation/nouveau?type=facture') {
  return render(
    <OverlayProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/facturation" element={<FacturationLayout />}>
            <Route path="nouveau" element={<FacturationComposerPage />} />
            <Route path="documents" element={<div>documents-outlet</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </OverlayProvider>,
  )
}

beforeEach(() => {
  cleanup()
  delete document.body.dataset.fpFocus
  delete document.body.dataset.fpFullFocus
})

afterEach(() => {
  cleanup()
  delete document.body.dataset.fpFocus
  delete document.body.dataset.fpFullFocus
})

describe('FF01–FF10 Route & shell Focus', () => {
  it('FF01 — shell full-focus page désactivé ; modal path détecté', () => {
    expect(isComposerFullFocusPath('/facturation/nouveau')).toBe(false)
    expect(isComposerFullFocusPath('/facturation/documents/new')).toBe(false)
    expect(isComposerModalPath('/facturation/documents/new')).toBe(true)
    expect(isComposerModalPath('/facturation/documents')).toBe(false)
    expect(isComposerModalPath('/dashboard')).toBe(false)
  })

  it('FF02 — FacturationLayout ne force plus full-focus page', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    const root = document.querySelector('.fp-spaces')
    expect(root).toBeTruthy()
    expect(root).not.toHaveClass('fp-spaces--full-focus')
    expect(root).toHaveAttribute('data-fp-full-focus', 'false')
  })

  it('FF03 — nav espaces Facturation visible (modal overlay, pas page Focus)', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    const nav = document.querySelector('.fp-spaces__nav')
    expect(nav).toBeTruthy()
    expect(nav).not.toHaveAttribute('hidden')
  })

  it('FF04 — data-composer-full-focus sur layout', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('[data-composer-full-focus="true"]')).toBeTruthy()
  })

  it('FF05 — body dataset full focus (page mode)', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.body.dataset.fpFullFocus).toBe('true')
  })

  it('FF06 — deep link type=devis en Focus layout', async () => {
    renderComposer('/facturation/nouveau?type=devis')
    expect(await screen.findByRole('heading', { name: 'Nouveau devis' })).toBeInTheDocument()
    expect(document.querySelector('[data-composer-full-focus="true"]')).toBeTruthy()
  })

  it('FF07 — deep link type=avoir en Focus', async () => {
    renderComposer('/facturation/nouveau?type=avoir')
    expect(await screen.findByRole('heading', { name: 'Nouvel avoir' })).toBeInTheDocument()
  })

  it('FF08 — sans type → message in-page (pas redirect)', async () => {
    render(
      <OverlayProvider>
        <MemoryRouter initialEntries={['/facturation/nouveau']}>
          <Routes>
            <Route path="/facturation/nouveau" element={<FacturationComposerPage />} />
            <Route path="/facturation/documents" element={<div>docs-create</div>} />
          </Routes>
        </MemoryRouter>
      </OverlayProvider>,
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(/Type de document manquant/i)
    expect(screen.queryByText('docs-create')).not.toBeInTheDocument()
  })

  it('FF09 — useComposerFocus hideProductSidebar', () => {
    function Probe() {
      const f = useComposerFocus({ initialEnabled: true })
      return (
        <span data-testid="flags">
          {f.hideProductSidebar ? 'sidebar-off' : 'sidebar-on'}:{f.hideChromeExtras ? 'chrome-off' : 'chrome-on'}
        </span>
      )
    }
    render(<Probe />)
    expect(screen.getByTestId('flags')).toHaveTextContent('sidebar-off:chrome-off')
  })

  it('FF10 — region a11y Création de document', async () => {
    renderComposer()
    expect(
      await screen.findByRole('region', { name: /création de document/i }),
    ).toBeInTheDocument()
  })
})

describe('FF11–FF20 Header Focus', () => {
  it('FF11 — bouton retour Documents', async () => {
    renderComposer()
    expect(await screen.findByRole('button', { name: 'Documents' })).toBeInTheDocument()
  })

  it('FF12 — Annuler secondaire', async () => {
    renderComposer()
    expect(await screen.findByRole('button', { name: 'Annuler' })).toBeInTheDocument()
  })

  it('FF13 — primaire Enregistrer brouillon', async () => {
    renderComposer()
    expect(await screen.findByRole('button', { name: /enregistrer brouillon/i })).toBeInTheDocument()
  })

  it('FF14 — header Focus landmark', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('[aria-label="Barre Focus document"]')).toBeTruthy()
  })

  it('FF15 — ComposerFocusLayout structure', () => {
    render(
      <ComposerFocusLayout
        definition={focusDef()}
        onBack={() => {}}
        preview={<div data-testid="prev">P</div>}
      >
        <p>editor</p>
      </ComposerFocusLayout>,
    )
    expect(document.querySelector('.elf-cmp-focus__workspace')).toBeTruthy()
    expect(document.querySelector('.elf-cmp-focus__editor')).toBeTruthy()
    expect(document.querySelector('.elf-cmp-focus__preview')).toBeTruthy()
    expect(screen.getByTestId('prev')).toBeInTheDocument()
  })

  it('FF16 — max 1 primaire dans FocusLayout', () => {
    render(
      <ComposerFocusLayout
        definition={focusDef()}
        primaryActions={[
          { id: 'a', label: 'Primaire A', tone: 'primary', onClick: () => {} },
          { id: 'b', label: 'Primaire B', tone: 'primary', onClick: () => {} },
        ]}
        secondaryActions={[
          { id: 'c', label: 'Sec C', tone: 'ghost', onClick: () => {} },
          { id: 'd', label: 'Sec D', tone: 'secondary', onClick: () => {} },
          { id: 'e', label: 'Sec E', tone: 'secondary', onClick: () => {} },
        ]}
      >
        x
      </ComposerFocusLayout>,
    )
    expect(screen.getByRole('button', { name: 'Primaire A' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Primaire B' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sec C' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sec D' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sec E' })).not.toBeInTheDocument()
  })

  it('FF17 — type document visible', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByText('Facture', { selector: '.elf-cmp-status__type' })).toBeInTheDocument()
  })

  it('FF18 — pas de Dashboard dans Focus', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.queryByRole('button', { name: 'Dashboard' })).not.toBeInTheDocument()
  })

  it('FF19 — headerCenter points à vérifier si issues', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(document.querySelector('.fp-composer-header-summary')).toHaveTextContent(/à vérifier/i)
  })

  it('FF20 — progress légère présente', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('.elf-cmp-progress')).toBeTruthy()
  })
})

describe('FF21–FF30 Workspace & sections', () => {
  it('FF21 — sections Client Lignes Conditions Notes', async () => {
    renderComposer()
    expect(await screen.findByRole('heading', { name: /^Client$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Produits$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Conditions$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Notes$/i })).toBeInTheDocument()
  })

  it('FF22 — Contrôles Paiement Totaux', async () => {
    renderComposer()
    expect(await screen.findByRole('heading', { name: /^Contrôles$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Paiement$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Totaux$/i })).toBeInTheDocument()
  })

  it('FF23 — pas de sidebar wizard', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('.elf-cmp-sidebar')).toBeNull()
  })

  it('FF24 — preview slot Focus', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('.elf-cmp-focus__preview')).toBeTruthy()
  })

  it('FF25 — toggle aperçu', async () => {
    renderComposer()
    expect(await screen.findByRole('button', { name: /aperçu/i })).toBeInTheDocument()
  })

  it('FF26 — ligne libre accessible', async () => {
    renderComposer()
    expect(await screen.findByRole('button', { name: 'Ajouter une ligne libre' })).toBeInTheDocument()
  })

  it('FF27 — data-fp-composer f131', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('[data-fp-composer="f131"]')).toBeTruthy()
  })

  it('FF28 — focusMode attr true', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('[data-focus-mode="true"]')).toBeTruthy()
  })

  it('FF29 — confirmation absente avant création', async () => {
    const { container } = renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(container.querySelector('.elf-cmp-focus__confirmation')).toBeNull()
  })

  it('FF30 — confirmation panel structure (layout)', () => {
    render(
      <ComposerFocusLayout
        definition={focusDef()}
        confirmation={
          <>
            <p className="elf-cmp-focus__confirmation-title">Document F-1 enregistré</p>
            <div className="elf-cmp-focus__confirmation-actions">
              <button type="button">Ouvrir le document</button>
              <button type="button">Revenir aux Documents</button>
              <button type="button">Créer un autre</button>
            </div>
          </>
        }
      >
        x
      </ComposerFocusLayout>,
    )
    expect(screen.getByText(/Document F-1 enregistré/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ouvrir le document' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Revenir aux Documents' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Créer un autre' })).toBeInTheDocument()
  })
})

describe('FF31–FF40 Exit, persist, a11y', () => {
  it('FF31 — confirm exit si dirty', async () => {
    const user = userEvent.setup()
    renderComposer()
    await user.click(await screen.findByRole('button', { name: 'Ajouter une ligne libre' }))
    await user.type(screen.getByLabelText(/libellé ligne 1/i), 'Presta')
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(await screen.findByText(/Quitter cette/i)).toBeInTheDocument()
  })

  it('FF32 — Documents back déclenche exit path', async () => {
    const user = userEvent.setup()
    renderComposer()
    await user.click(await screen.findByRole('button', { name: 'Documents' }))
    // draft vide → pas de confirm, navigation mockée via router MemoryRouter
    expect(screen.queryByText(/Quitter cette/i)).not.toBeInTheDocument()
  })

  it('FF33 — documents space hors Focus', () => {
    render(
      <MemoryRouter initialEntries={['/facturation/documents']}>
        <Routes>
          <Route path="/facturation" element={<FacturationLayout />}>
            <Route path="documents" element={<div>docs</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(document.querySelector('[data-fp-full-focus="true"]')).toBeNull()
    expect(screen.getByRole('navigation', { name: /espaces facturation/i })).toBeInTheDocument()
  })

  it('FF34 — ComposerFocusLayout preview collapsed', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    render(
      <ComposerFocusLayout
        definition={focusDef()}
        previewCollapsed
        onTogglePreview={onToggle}
        preview={<div>hidden-prev</div>}
      >
        x
      </ComposerFocusLayout>,
    )
    expect(screen.queryByText('hidden-prev')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /afficher l’aperçu/i }))
    expect(onToggle).toHaveBeenCalled()
  })

  it('FF35 — Escape ne ferme pas Composer (seulement overlays)', async () => {
    const user = userEvent.setup()
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    await user.keyboard('{Escape}')
    expect(screen.getByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
  })

  it('FF36 — preview aside landmark', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('complementary', { name: /aperçu document/i })).toBeInTheDocument()
  })

  it('FF37 — refresh path conserve type (re-render)', async () => {
    const { rerender } = renderComposer('/facturation/nouveau?type=facture')
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    rerender(
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
    expect(await screen.findByRole('heading', { name: 'Nouvelle facture' })).toBeInTheDocument()
    expect(document.querySelector('[data-composer-full-focus="true"]')).toBeTruthy()
  })

  it('FF38 — classes CSS full focus workspace', () => {
    render(
      <ComposerFocusLayout definition={focusDef()} preview={<div />}>
        <div className="elf-cmp-section">sec</div>
      </ComposerFocusLayout>,
    )
    expect(document.querySelector('.elf-cmp-focus')).toBeTruthy()
    expect(document.querySelector('.elf-cmp--focus')).toBeTruthy()
  })

  it('FF39 — actions group labelled', async () => {
    renderComposer()
    await screen.findByRole('heading', { name: 'Nouvelle facture' })
    expect(screen.getByRole('group', { name: /actions document/i })).toBeInTheDocument()
  })

  it('FF40 — export ComposerFocusLayout depuis framework', async () => {
    const mod = await import('../../composer-framework')
    expect(mod.ComposerFocusLayout).toBeTypeOf('function')
    expect(mod.useComposerFocus).toBeTypeOf('function')
  })
})
