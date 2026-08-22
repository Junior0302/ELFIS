/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { HomePlatformSidebar } from './HomePlatformSidebar'

const logout = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => ({
    logout,
    user: { first_name: 'Chris', last_name: 'Demo' },
    memberships: [
      {
        organization_id: 1,
        permissions: ['*', 'documents.read', 'users.manage', 'ai.analysis'],
      },
    ],
    orgId: 1,
  }),
}))

vi.mock('../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="product-mark">M</span>,
}))

describe('HomePlatformSidebar', () => {
  it('affiche la nav plateforme Home structurée', () => {
    render(
      <MemoryRouter>
        <HomePlatformSidebar onCollapsedChange={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('navigation', { name: /navigation plateforme/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /accueil/i })).toHaveAttribute('href', '/home')
    expect(screen.getByRole('link', { name: /favoris/i })).toHaveAttribute('href', '/home#home-spaces')
    expect(screen.getByRole('link', { name: /activité/i })).toHaveAttribute(
      'href',
      '/home#home-activity',
    )
    expect(screen.getByRole('link', { name: /notifications/i })).toHaveAttribute(
      'href',
      '/notifications',
    )
    expect(screen.getByRole('link', { name: /paramètres/i })).toHaveAttribute(
      'href',
      '/platform/settings',
    )
    expect(screen.getByRole('link', { name: /^organisation$/i })).toHaveAttribute(
      'href',
      '/platform/organization',
    )
    expect(screen.getByRole('link', { name: /^documents$/i })).toHaveAttribute(
      'href',
      '/platform/documents',
    )
    expect(screen.getByRole('link', { name: /^relations$/i })).toHaveAttribute(
      'href',
      '/platform/relations',
    )
    expect(screen.getByRole('link', { name: /communications/i })).toHaveAttribute(
      'href',
      '/platform/communications',
    )
    expect(screen.getByRole('link', { name: /aide/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /déconnexion/i })).toBeInTheDocument()
    expect(screen.getByText('ELFIS')).toBeInTheDocument()
    expect(screen.queryByText('ELFIS Core')).toBeNull()
  })
})

