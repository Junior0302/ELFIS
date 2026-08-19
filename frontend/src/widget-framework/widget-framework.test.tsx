/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  WidgetChartBody,
  WidgetContainer,
  WidgetEmpty,
  WidgetError,
  WidgetGrid,
  WidgetList,
  WidgetLoading,
  WidgetMetric,
  WidgetSection,
  WidgetStatusBadge,
  type WidgetDefinition,
} from './index'

function def(over: Partial<WidgetDefinition> = {}): WidgetDefinition {
  return {
    id: 'w1',
    title: 'Widget test',
    category: 'observe',
    status: 'ready',
    refreshable: true,
    source: 'Test',
    ...over,
  }
}

describe('ELFIS Widget Framework V1', () => {
  it('exporte les primitives', () => {
    expect(WidgetContainer).toBeTypeOf('function')
    expect(WidgetEmpty).toBeTypeOf('function')
    expect(WidgetError).toBeTypeOf('function')
    expect(WidgetLoading).toBeTypeOf('function')
    expect(WidgetStatusBadge).toBeTypeOf('function')
  })

  it('rend ready avec children et a11y titre', () => {
    render(
      <WidgetContainer definition={def({ status: 'ready' })}>
        <p>Contenu prêt</p>
      </WidgetContainer>,
    )
    expect(screen.getByRole('heading', { name: 'Widget test' })).toHaveAttribute(
      'id',
      'ew-title-w1',
    )
    expect(screen.getByText('Contenu prêt')).toBeInTheDocument()
    expect(document.querySelector('[data-widget-status="ready"]')).toBeTruthy()
    cleanup()
  })

  it('affiche loading skeleton', () => {
    render(<WidgetContainer definition={def({ status: 'loading' })}>hidden</WidgetContainer>)
    expect(screen.getByLabelText(/chargement/i)).toBeInTheDocument()
    expect(screen.queryByText('hidden')).not.toBeInTheDocument()
    cleanup()
  })

  it('affiche empty', () => {
    render(
      <WidgetContainer
        definition={def({
          status: 'empty',
          emptyTitle: 'Aucune donnée',
          emptyDescription: 'Revenez plus tard',
        })}
      />,
    )
    expect(screen.getByText('Aucune donnée')).toBeInTheDocument()
    expect(screen.getByText('Revenez plus tard')).toBeInTheDocument()
    cleanup()
  })

  it('affiche error + retry', async () => {
    const onRetry = vi.fn()
    const user = userEvent.setup()
    render(
      <WidgetContainer
        definition={def({ status: 'error', errorMessage: 'Échec réseau', refreshable: false })}
        onRetry={onRetry}
      />,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Échec réseau')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /réessayer/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
    cleanup()
  })

  it('affiche refreshing avec children et badge', () => {
    render(
      <WidgetContainer definition={def({ status: 'refreshing' })}>
        <span>Toujours visible</span>
      </WidgetContainer>,
    )
    expect(screen.getByText('Toujours visible')).toBeInTheDocument()
    expect(screen.getByText(/actualisation/i)).toBeInTheDocument()
    cleanup()
  })

  it('appelle onRefresh via bouton accessible', async () => {
    const onRefresh = vi.fn()
    const user = userEvent.setup()
    render(
      <WidgetContainer definition={def({ status: 'ready', refreshable: true })} onRefresh={onRefresh}>
        ok
      </WidgetContainer>,
    )
    await user.click(screen.getByRole('button', { name: /actualiser widget test/i }))
    expect(onRefresh).toHaveBeenCalledTimes(1)
    cleanup()
  })

  it('applique le variant compact et footer secondaire', () => {
    render(
      <WidgetContainer
        definition={def({
          status: 'ready',
          variant: 'compact',
          source: 'Engine',
          lastUpdatedAt: '2026-08-02T12:00:00Z',
        })}
      >
        <WidgetMetric value="42" detail="détail" />
      </WidgetContainer>,
    )
    const root = document.querySelector('[data-widget-variant="compact"]')
    expect(root).toBeTruthy()
    expect(root?.className).toMatch(/ew-widget--compact/)
    expect(document.querySelector('.ew-footer--secondary')).toBeTruthy()
    expect(screen.getByText('42')).toBeInTheDocument()
    cleanup()
  })

  it('exporte helpers grid / section / chart / list', () => {
    render(
      <WidgetSection id="sec" title="Section test">
        <WidgetGrid columns={3}>
          <WidgetChartBody summary="résumé a11y">
            <svg role="img" aria-label="chart" />
          </WidgetChartBody>
          <WidgetList>
            <li>Item</li>
          </WidgetList>
        </WidgetGrid>
      </WidgetSection>,
    )
    expect(screen.getByRole('heading', { name: 'Section test' })).toHaveAttribute('id', 'sec')
    expect(screen.getByText('Item')).toBeInTheDocument()
    expect(screen.getByText('résumé a11y')).toHaveClass('visually-hidden')
    cleanup()
  })
})
