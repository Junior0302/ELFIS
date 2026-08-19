/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { PLATFORM_NAV_ITEMS, filterPlatformNav } from './platformNavModel'
import { PlatformNavigation } from './PlatformNavigation'
import PlatformWorkspaceLayout from './PlatformWorkspaceLayout'

vi.mock('../auth', () => ({
  useAuth: () => ({
    logout: vi.fn(),
    orgId: 1,
    memberships: [
      { organization_id: 1, permissions: ['*', 'documents.read', 'users.manage', 'ai.analysis'] },
    ],
    user: { first_name: 'Chris' },
  }),
}))

beforeEach(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
})

vi.mock('../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="mark">M</span>,
}))

vi.mock('../unified-platform', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../unified-platform')>()
  return {
    ...actual,
    PilotWorkspace: ({
      children,
      nav,
      pilotId,
    }: {
      children: ReactNode
      nav?: ReactNode | ((api: { closeMobileNav: () => void }) => ReactNode)
      pilotId: string
    }) => (
      <div data-testid="platform-shell" data-product={pilotId}>
        <aside data-testid="platform-sidebar">
          {typeof nav === 'function' ? nav({ closeMobileNav: () => undefined }) : nav}
        </aside>
        <main>{children}</main>
      </div>
    ),
  }
})

vi.mock('../platform-shell', () => ({
  PlatformShell: ({
    children,
    sidebar,
    productId,
  }: {
    children: ReactNode
    sidebar?: ReactNode | ((api: { closeMobileNav: () => void }) => ReactNode)
    productId: string
  }) => (
    <div data-testid="platform-shell" data-product={productId}>
      <aside data-testid="platform-sidebar">
        {typeof sidebar === 'function' ? sidebar({ closeMobileNav: () => undefined }) : sidebar}
      </aside>
      <main>{children}</main>
    </div>
  ),
}))

describe('S1.1 platform workspace', () => {
  it('nav modèle couvre les surfaces cibles structurées', () => {
    const ids = PLATFORM_NAV_ITEMS.map((i) => i.id)
    expect(ids).toContain('home')
    expect(ids).toContain('organization')
    expect(ids).toContain('members')
    expect(ids).toContain('relations')
    expect(ids).toContain('documents')
    expect(ids).toContain('communications')
    expect(ids).toContain('intelligence')
    expect(ids).toContain('settings')
    expect(ids).toContain('favorites')
    expect(ids).toContain('search')
  })

  it('filtre permissions — masque members sans users.manage', () => {
    const visible = filterPlatformNav(PLATFORM_NAV_ITEMS, (p) => !p || p === 'documents.read')
    expect(visible.some((i) => i.id === 'members')).toBe(false)
    expect(visible.some((i) => i.id === 'documents')).toBe(true)
    expect(visible.some((i) => i.id === 'home')).toBe(true)
  })

  it('PlatformNavigation expose les liens ELFIS', () => {
    render(
      <MemoryRouter>
        <PlatformNavigation onCollapsedChange={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('navigation', { name: /navigation plateforme/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^organisation$/i })).toHaveAttribute(
      'href',
      '/platform/organization',
    )
    expect(screen.getByRole('link', { name: /membres/i })).toHaveAttribute('href', '/platform/members')
    expect(screen.getByRole('link', { name: /^documents$/i })).toHaveAttribute(
      'href',
      '/platform/documents',
    )
    expect(screen.getByRole('link', { name: /communications/i })).toHaveAttribute(
      'href',
      '/platform/communications',
    )
    expect(screen.getByRole('link', { name: /intelligence elfis/i })).toHaveAttribute(
      'href',
      '/platform/aura',
    )
    expect(screen.getByRole('link', { name: /^relations$/i })).toHaveAttribute(
      'href',
      '/platform/relations',
    )
    expect(screen.getByText('ELFIS')).toBeInTheDocument()
    expect(screen.queryByText('ELFIS Core')).toBeNull()
  })

  it('PlatformWorkspaceLayout = elfis-core, pas Compta/Sales sidebar', () => {
    render(
      <MemoryRouter initialEntries={['/platform/organization']}>
        <Routes>
          <Route element={<PlatformWorkspaceLayout />}>
            <Route path="platform/organization" element={<div>Org surface</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('platform-shell')).toHaveAttribute('data-product', 'elfis-core')
    expect(screen.getByText('Org surface')).toBeInTheDocument()
  })
})

