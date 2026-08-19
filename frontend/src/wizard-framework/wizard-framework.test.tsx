/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  WizardActions,
  WizardContainer,
  WizardProgress,
  WizardSidebar,
  WizardStep,
  WizardSummary,
  WizardValidation,
  useWizardNavigation,
  type WizardDefinition,
  type WizardStepDefinition,
} from './index'

const STEPS: WizardStepDefinition[] = [
  { id: 'a', label: 'Étape A', description: 'Première' },
  { id: 'b', label: 'Étape B' },
  { id: 'c', label: 'Étape C', optional: true },
]

function def(over: Partial<WizardDefinition> = {}): WizardDefinition {
  return {
    id: 'wiz-test',
    title: 'Wizard test',
    description: 'Description test',
    steps: STEPS,
    currentStepId: 'a',
    stepStatuses: { a: 'current', b: 'upcoming', c: 'upcoming' },
    ...over,
  }
}

function NavHarness({ canLeave }: { canLeave?: (id: string) => boolean }) {
  const nav = useWizardNavigation({ steps: STEPS, canLeaveStep: canLeave })
  return (
    <div>
      <p data-testid="current">{nav.currentStepId}</p>
      <button type="button" onClick={nav.goNext} disabled={!nav.canGoNext}>
        next
      </button>
      <button type="button" onClick={nav.goBack} disabled={!nav.canGoBack}>
        back
      </button>
      <button type="button" onClick={() => nav.goToStep('c')}>
        jump-c
      </button>
    </div>
  )
}

describe('ELFIS Wizard Framework V1', () => {
  it('exporte les primitives', () => {
    expect(WizardContainer).toBeTypeOf('function')
    expect(WizardStep).toBeTypeOf('function')
    expect(WizardSidebar).toBeTypeOf('function')
    expect(WizardProgress).toBeTypeOf('function')
    expect(WizardValidation).toBeTypeOf('function')
    expect(WizardSummary).toBeTypeOf('function')
    expect(WizardActions).toBeTypeOf('function')
    expect(useWizardNavigation).toBeTypeOf('function')
  })

  it('rend container + step + a11y progression', () => {
    render(
      <WizardContainer definition={def()}>
        <WizardStep id="a" title="Contenu A">
          <p>Hello wizard</p>
        </WizardStep>
      </WizardContainer>,
    )
    expect(screen.getByRole('heading', { name: 'Wizard test' })).toBeInTheDocument()
    expect(screen.getByText('Hello wizard')).toBeInTheDocument()
    expect(document.querySelector('[data-wizard-id="wiz-test"]')).toBeTruthy()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    cleanup()
  })

  it('affiche validation vide honnête', () => {
    render(<WizardValidation issues={[]} emptyMessage="Aucun contrôle à signaler" />)
    expect(screen.getByText('Aucun contrôle à signaler')).toBeInTheDocument()
    cleanup()
  })

  it('affiche issues de validation', () => {
    render(
      <WizardValidation
        issues={[
          { id: '1', severity: 'warning', message: 'Client incomplet' },
          { id: '2', severity: 'info', message: 'TVA à 0 %' },
        ]}
      />,
    )
    expect(screen.getByText('Client incomplet')).toBeInTheDocument()
    expect(screen.getByText('TVA à 0 %')).toBeInTheDocument()
    cleanup()
  })

  it('navigue next/back via useWizardNavigation', async () => {
    const user = userEvent.setup()
    render(<NavHarness />)
    expect(screen.getByTestId('current')).toHaveTextContent('a')
    await user.click(screen.getByRole('button', { name: 'next' }))
    expect(screen.getByTestId('current')).toHaveTextContent('b')
    await user.click(screen.getByRole('button', { name: 'back' }))
    expect(screen.getByTestId('current')).toHaveTextContent('a')
    cleanup()
  })

  it('bloque next si canLeaveStep false', async () => {
    const user = userEvent.setup()
    render(<NavHarness canLeave={() => false} />)
    expect(screen.getByRole('button', { name: 'next' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'next' }))
    expect(screen.getByTestId('current')).toHaveTextContent('a')
    cleanup()
  })

  it('empêche le saut trop loin vers une étape future', async () => {
    const user = userEvent.setup()
    render(<NavHarness />)
    await user.click(screen.getByRole('button', { name: 'jump-c' }))
    expect(screen.getByTestId('current')).toHaveTextContent('a')
    cleanup()
  })

  it('rend résumé et actions', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()
    render(
      <>
        <WizardSummary items={[{ label: 'Type', value: 'Facture' }]} />
        <WizardActions
          actions={[{ id: 'go', label: 'Continuer', tone: 'primary', onClick }]}
        />
      </>,
    )
    expect(screen.getByText('Facture')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Continuer' }))
    expect(onClick).toHaveBeenCalledTimes(1)
    cleanup()
  })
})
