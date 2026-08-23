/**
 * Phase 3 — WorkspaceSidebar générique.
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { WorkspaceSidebar } from './WorkspaceSidebar'
import {
  commercialWorkspaceConfig,
  documentsWorkspaceConfig,
  financeWorkspaceConfig,
  isWorkspaceNavLeafActive,
} from './index'
import { findActiveWorkspaceGroup } from './navHelpers'

afterEach(() => {
  cleanup()
})

vi.mock('../components/NavIcons', () => ({
  navIcons: new Proxy(
    {},
    {
      get: () => () => <span data-testid="nav-icon" />,
    },
  ),
}))

function renderSidebar(
  workspace: typeof financeWorkspaceConfig,
  path: string,
  opts?: {
    collapsed?: boolean
    can?: (p?: string) => boolean
    ariaLabel?: string
  },
) {
  const onCollapsedChange = vi.fn()
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="*"
          element={
            <WorkspaceSidebar
              workspace={workspace}
              navId="test-workspace-nav"
              ariaLabel={opts?.ariaLabel ?? 'Navigation test'}
              collapsed={opts?.collapsed ?? false}
              onCollapsedChange={onCollapsedChange}
              can={opts?.can}
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('WorkspaceSidebar', () => {
  it('rend les groupes Finance avec chevrons', () => {
    renderSidebar(financeWorkspaceConfig, '/dashboard', { ariaLabel: 'Navigation Finance' })
    expect(screen.getByRole('navigation', { name: 'Navigation Finance' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Facturation' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Finance' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Tableau de bord' })).toBeTruthy()
  })

  it('déplie Finance et montre Trésorerie + Vue d’ensemble', () => {
    renderSidebar(financeWorkspaceConfig, '/finance', { ariaLabel: 'Navigation Finance' })
    const financeBtn = screen.getByRole('button', { name: 'Finance' })
    expect(financeBtn).toHaveAttribute('aria-expanded', 'true')
    const group = financeBtn.closest('.nav-group') as HTMLElement
    expect(within(group).getByRole('link', { name: /^Vue d’ensemble$/i })).toBeTruthy()
    expect(within(group).getByRole('link', { name: /^Trésorerie$/i })).toBeTruthy()
  })

  it('contextual — seule Vue d’ensemble active sur /finance', () => {
    renderSidebar(financeWorkspaceConfig, '/finance', { ariaLabel: 'Navigation Finance' })
    const overview = document.querySelector('[data-nav-leaf="finance-overview"]')
    const tresorerie = document.querySelector('[data-nav-leaf="tresorerie"]')
    expect(overview).toHaveClass('is-active')
    expect(overview).toHaveAttribute('aria-current', 'page')
    expect(tresorerie).not.toHaveClass('is-active')
    expect(tresorerie?.getAttribute('aria-current')).toBeNull()
  })

  it('applique data-workspace et couleur accent', () => {
    renderSidebar(financeWorkspaceConfig, '/dashboard')
    const scope = document.querySelector('[data-workspace="finance"]') as HTMLElement
    expect(scope).toBeTruthy()
    expect(scope.style.getPropertyValue('--workspace-accent')).toBe('#16A34A')
  })

  it('collapsed — mode is-collapsed + flyout', () => {
    renderSidebar(financeWorkspaceConfig, '/finance', {
      collapsed: true,
      ariaLabel: 'Navigation Finance',
    })
    const nav = screen.getByRole('navigation', { name: 'Navigation Finance' })
    expect(nav.className).toMatch(/is-collapsed/)
    const group = screen.getByRole('button', { name: 'Finance' }).closest('.nav-group') as HTMLElement
    fireEvent.mouseEnter(group)
    expect(within(group).getByRole('menu', { name: 'Finance' })).toBeTruthy()
  })

  it('Finance — pas de lien Banque (sync = menu ELFIS Core)', () => {
    renderSidebar(financeWorkspaceConfig, '/finance', {
      ariaLabel: 'Navigation Finance',
    })
    expect(screen.queryByRole('link', { name: 'Banque' })).toBeNull()
    expect(screen.queryByRole('link', { name: /synchronisation bancaire/i })).toBeNull()
    expect(screen.getByRole('link', { name: 'TVA' })).toBeTruthy()
  })

  it('Commercial — pas de devis/catalogue/facturation', () => {
    renderSidebar(commercialWorkspaceConfig, '/sales', { ariaLabel: 'Navigation Commercial' })
    expect(screen.queryByRole('link', { name: 'Devis' })).toBeNull()
    expect(screen.queryByRole('link', { name: /catalogue/i })).toBeNull()
    expect(screen.getByRole('button', { name: 'Prospection' })).toBeTruthy()
  })

  it('Documents — minimal Vue d’ensemble', () => {
    renderSidebar(documentsWorkspaceConfig, '/platform/documents', {
      ariaLabel: 'Navigation Documents',
    })
    const scope = document.querySelector('[data-workspace="documents"]') as HTMLElement
    expect(scope.style.getPropertyValue('--workspace-accent')).toBe('#7C3AED')
    const overview = document.querySelector('[data-nav-leaf="documents-overview"]')
    expect(overview).toBeTruthy()
    expect(overview).toHaveAttribute('href', '/platform/documents')
  })

  it('isWorkspaceNavLeafActive — policies', () => {
    const group = financeWorkspaceConfig.navigationGroups.find((g) => g.id === 'pilotage')!
    const overview = group.children.find((c) => c.id === 'finance-overview')!
    const tresorerie = group.children.find((c) => c.id === 'tresorerie')!
    expect(isWorkspaceNavLeafActive(overview, '/finance', group.children)).toBe(true)
    expect(isWorkspaceNavLeafActive(tresorerie, '/finance', group.children)).toBe(false)
  })

  it('findActiveWorkspaceGroup préfère clients si demandé', () => {
    const groups = commercialWorkspaceConfig.navigationGroups
    const active = findActiveWorkspaceGroup(
      '/sales/companies',
      groups,
      (best, candidate) => candidate.id === 'clients' && best?.id === 'prospection',
    )
    expect(active?.id).toBe('clients')
  })
})
