/**
 * Phase 4 — primitives page / KPI workspace.
 * @vitest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WorkspaceKpiCard } from './WorkspaceKpiCard'
import { WorkspacePageHeader } from './WorkspacePageHeader'

describe('WorkspacePageHeader', () => {
  it('rend titre, description et eyebrow', () => {
    render(
      <WorkspacePageHeader
        eyebrow="Finance"
        title="Facturation"
        description="Créez et pilotez vos documents commerciaux"
      />,
    )
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Facturation' })).toBeInTheDocument()
    expect(screen.getByText('Créez et pilotez vos documents commerciaux')).toBeInTheDocument()
  })

  it('expose la classe workspace-page-header', () => {
    const { container } = render(<WorkspacePageHeader title="Test" />)
    expect(container.querySelector('.workspace-page-header')).toBeTruthy()
  })
})

describe('WorkspaceKpiCard', () => {
  it('affiche label et valeur sans inventer de métrique', () => {
    render(<WorkspaceKpiCard title="Trésorerie" value="12 000 €" />)
    expect(screen.getByText('Trésorerie')).toBeInTheDocument()
    expect(screen.getByText('12 000 €')).toBeInTheDocument()
  })

  it('applique la barre d’accent discrète', () => {
    const { container } = render(
      <WorkspaceKpiCard title="CA" value="1" accentBar className="x" />,
    )
    expect(container.querySelector('.workspace-kpi-card--accent-bar')).toBeTruthy()
  })
})
