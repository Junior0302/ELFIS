/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  ComposerActions,
  ComposerCard,
  ComposerFocusLayout,
  ComposerLayout,
  ComposerPreview,
  ComposerProgress,
  ComposerSection,
  ComposerSidebar,
  ComposerValidation,
  useComposerFocus,
  type ComposerDefinition,
  type ComposerStepDefinition,
} from './index'

const STEPS: ComposerStepDefinition[] = [
  { id: 'a', label: 'Étape A', description: 'Première' },
  { id: 'b', label: 'Étape B' },
  { id: 'c', label: 'Étape C', optional: true },
]

function def(over: Partial<ComposerDefinition> = {}): ComposerDefinition {
  return {
    id: 'cmp-test',
    title: 'Document test',
    documentType: 'Facture',
    statusLabel: 'Brouillon',
    steps: STEPS,
    currentStepId: 'a',
    stepStatuses: { a: 'current', b: 'upcoming', c: 'upcoming' },
    ...over,
  }
}

function FocusHarness() {
  const focus = useComposerFocus({
    initialEnabled: true,
    exitTargets: [
      { id: 'dashboard', label: 'Dashboard', href: '/dashboard' },
      { id: 'docs', label: 'Documents', href: '/facturation/documents' },
    ],
    onExitNavigate: vi.fn(),
  })
  return (
    <div>
      <p data-testid="focus">{focus.focusMode ? 'on' : 'off'}</p>
      <p data-testid="hide-nav">{focus.hideSecondaryNav ? 'yes' : 'no'}</p>
      <button type="button" onClick={focus.toggleFocus}>
        toggle
      </button>
      <button type="button" onClick={() => focus.exitTo('docs')}>
        exit-docs
      </button>
    </div>
  )
}

describe('ELFIS Composer Framework V1', () => {
  it('exporte les primitives', () => {
    expect(ComposerLayout).toBeTypeOf('function')
    expect(ComposerSidebar).toBeTypeOf('function')
    expect(ComposerProgress).toBeTypeOf('function')
    expect(ComposerPreview).toBeTypeOf('function')
    expect(ComposerValidation).toBeTypeOf('function')
    expect(ComposerSection).toBeTypeOf('function')
    expect(ComposerCard).toBeTypeOf('function')
    expect(ComposerActions).toBeTypeOf('function')
    expect(useComposerFocus).toBeTypeOf('function')
  })

  it('rend layout + a11y progression + data attributes', () => {
    render(
      <ComposerLayout definition={def()} focusMode>
        <ComposerSection id="a" title="Contenu A">
          <p>Hello composer</p>
        </ComposerSection>
      </ComposerLayout>,
    )
    expect(screen.getByRole('heading', { name: 'Document test' })).toBeInTheDocument()
    expect(screen.getByText('Hello composer')).toBeInTheDocument()
    expect(document.querySelector('[data-composer-id="cmp-test"]')).toBeTruthy()
    expect(document.querySelector('[data-focus-mode="true"]')).toBeTruthy()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    cleanup()
  })

  it('affiche sidebar avec états d’étapes', () => {
    cleanup()
    render(
      <ComposerSidebar
        definition={def({
          stepStatuses: { a: 'completed', b: 'current', c: 'blocked' },
          currentStepId: 'b',
        })}
      />,
    )
    expect(screen.getByRole('navigation', { name: /étapes du document/i })).toBeInTheDocument()
    expect(screen.getByText('Terminé')).toBeInTheDocument()
    expect(screen.getByText('En cours')).toBeInTheDocument()
    expect(screen.getByText('Bloqué')).toBeInTheDocument()
    cleanup()
  })

  it('navigue les étapes autorisées via onSelectStep', async () => {
    cleanup()
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(
      <ComposerSidebar
        definition={def({
          currentStepId: 'a',
          stepStatuses: { a: 'current', b: 'upcoming', c: 'upcoming' },
        })}
        onSelectStep={onSelect}
      />,
    )
    const sidebar = screen.getByRole('navigation', { name: /étapes du document/i })
    await user.click(within(sidebar).getByRole('button', { name: /étape b/i }))
    expect(onSelect).toHaveBeenCalledWith('b')
    cleanup()
  })

  it('rend preview empty / loading / error / ready', () => {
    const { rerender } = render(<ComposerPreview state="empty" />)
    expect(screen.getByText(/enregistrez un brouillon/i)).toBeInTheDocument()
    rerender(<ComposerPreview state="loading" />)
    expect(screen.getByText(/chargement/i)).toBeInTheDocument()
    rerender(<ComposerPreview state="error" errorMessage="PDF cassé" />)
    expect(screen.getByText('PDF cassé')).toBeInTheDocument()
    rerender(
      <ComposerPreview state="ready">
        <div>pdf-ready</div>
      </ComposerPreview>,
    )
    expect(screen.getByText('pdf-ready')).toBeInTheDocument()
    cleanup()
  })

  it('expose contrôles zoom / largeur / plein écran (FE only)', async () => {
    const user = userEvent.setup()
    const onZoomIn = vi.fn()
    const onFitWidth = vi.fn()
    const onToggleFullscreen = vi.fn()
    render(
      <ComposerPreview
        state="ready"
        zoomPercent={110}
        onZoomIn={onZoomIn}
        onFitWidth={onFitWidth}
        fitWidth
        onToggleFullscreen={onToggleFullscreen}
      >
        <div>content</div>
      </ComposerPreview>,
    )
    expect(screen.getByText('110 %')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '+' }))
    expect(onZoomIn).toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /largeur/i }))
    expect(onFitWidth).toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /plein écran/i }))
    expect(onToggleFullscreen).toHaveBeenCalled()
    cleanup()
  })

  it('affiche validation suggestion + empty', () => {
    render(<ComposerValidation issues={[]} emptyMessage="OK" />)
    expect(screen.getByText('OK')).toBeInTheDocument()
    cleanup()
    render(
      <ComposerValidation
        issues={[
          { id: '1', severity: 'suggestion', message: 'Vérifier l’échéance' },
          { id: '2', severity: 'warning', message: 'Client incomplet' },
        ]}
      />,
    )
    expect(screen.getByText('Vérifier l’échéance')).toBeInTheDocument()
    expect(screen.getByText('Client incomplet')).toBeInTheDocument()
    cleanup()
  })

  it('focus mode basique — toggle + hideSecondaryNav', async () => {
    const user = userEvent.setup()
    render(<FocusHarness />)
    expect(screen.getByTestId('focus')).toHaveTextContent('on')
    expect(screen.getByTestId('hide-nav')).toHaveTextContent('yes')
    await user.click(screen.getByRole('button', { name: 'toggle' }))
    expect(screen.getByTestId('focus')).toHaveTextContent('off')
    expect(screen.getByTestId('hide-nav')).toHaveTextContent('no')
    cleanup()
  })

  it('layout desktop expose slots sidebar / editor / preview', () => {
    render(
      <ComposerLayout
        definition={def()}
        showPreview
        preview={<ComposerPreview state="empty" />}
        inspector={<div>inspector-slot</div>}
      >
        <p>editor-slot</p>
      </ComposerLayout>,
    )
    expect(screen.getByText('editor-slot')).toBeInTheDocument()
    expect(screen.getByText('inspector-slot')).toBeInTheDocument()
    expect(document.querySelector('.elf-cmp__layout--sidebar')).toBeTruthy()
    expect(document.querySelector('.elf-cmp__layout--preview')).toBeTruthy()
    cleanup()
  })

  it('ComposerFocusLayout full focus structure', () => {
    render(
      <ComposerFocusLayout definition={def()} onBack={() => {}} preview={<div>prev</div>}>
        <ComposerSection id="x" title="Sec">
          body
        </ComposerSection>
      </ComposerFocusLayout>,
    )
    expect(document.querySelector('[data-composer-full-focus="true"]')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Documents' })).toBeInTheDocument()
    cleanup()
  })
})
