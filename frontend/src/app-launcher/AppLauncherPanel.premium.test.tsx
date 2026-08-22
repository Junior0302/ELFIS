/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AppLauncherPanel } from './AppLauncherPanel'
import { getKnownSpaRoutes } from './productEntryRoutes'
import type { LauncherResolveContext } from './launcher.types'

function resetStorage() {
  try {
    window.localStorage?.removeItem('elfis_last_product')
    window.localStorage?.removeItem('elfis_last_product_at')
  } catch {
    /* ignore */
  }
}

const resolveContext: LauncherResolveContext = {
  currentProductId: 'comptapilot',
  availableRoutes: getKnownSpaRoutes(),
}

describe('AppLauncherPanel spaces hub v1', () => {
  beforeEach(() => {
    cleanup()
    resetStorage()
  })
  afterEach(() => {
    cleanup()
    resetStorage()
  })

  it('structure signature : header, search, continuer fallback, espaces, bientôt, footer', () => {
    const { container } = render(
      <MemoryRouter>
        <AppLauncherPanel resolveContext={resolveContext} onSelect={() => undefined} />
      </MemoryRouter>,
    )
    expect(container.querySelector('[data-launcher="spaces-hub-v1"]')).toBeTruthy()
    expect(screen.getByText('Espaces ELFIS')).toBeInTheDocument()
    expect(
      screen.getByText(/accédez à tous les métiers de votre entreprise depuis un seul espace/i),
    ).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/rechercher un espace, une fonction/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^continuer$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /commencer dans finance/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /espaces métier/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /espaces à venir/i })).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('Commercial')).toBeInTheDocument()
    expect(document.querySelector('[data-space="documents"]')).toBeTruthy()
    expect(screen.getByText('Ressources Humaines')).toBeInTheDocument()
    expect(screen.getByText('Pilotage financier et trésorerie.')).toBeInTheDocument()
    expect(screen.queryByText('Moteur ComptaPilot')).toBeNull()
    expect(screen.queryByText('Marketplace')).toBeNull()
    expect(screen.getAllByRole('link', { name: /accueil elfis/i })[0]).toHaveAttribute('href', '/home')
    expect(screen.getByRole('link', { name: /^organisation$/i })).toHaveAttribute(
      'href',
      '/platform/organization',
    )
    expect(screen.getByRole('link', { name: /^documents$/i })).toHaveAttribute(
      'href',
      '/platform/documents',
    )
    expect(screen.getByRole('link', { name: /paramètres/i })).toHaveAttribute(
      'href',
      '/platform/settings',
    )
    expect(screen.queryByRole('link', { name: /découvrir/i })).toBeNull()
  })

  it('recherche locale + empty state + clear', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AppLauncherPanel resolveContext={resolveContext} onSelect={() => undefined} />
      </MemoryRouter>,
    )
    const input = screen.getByPlaceholderText(/rechercher un espace, une fonction/i)
    await user.type(input, 'zzzz-introuvable')
    expect(screen.getByText(/aucun espace ne correspond/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /effacer la recherche/i }))
    expect(input).toHaveValue('')
    expect(screen.getByRole('heading', { name: /espaces métier/i })).toBeInTheDocument()
  })

  it('filtre par alias métier', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AppLauncherPanel resolveContext={resolveContext} onSelect={() => undefined} />
      </MemoryRouter>,
    )
    await user.type(screen.getByPlaceholderText(/rechercher un espace, une fonction/i), 'Pipeline')
    expect(screen.getAllByText('Commercial').length).toBeGreaterThan(0)
    expect(screen.queryByText('Ressources Humaines')).toBeNull()
  })

  it('continuer avec lastProduct réel uniquement', () => {
    try {
      window.localStorage?.setItem('elfis_last_product', 'salespilot')
    } catch {
      /* storage may be unavailable in some runners */
    }
    render(
      <MemoryRouter>
        <AppLauncherPanel resolveContext={resolveContext} onSelect={() => undefined} />
      </MemoryRouter>,
    )
    const hasStorage = Boolean(window.localStorage?.getItem?.('elfis_last_product'))
    if (hasStorage) {
      expect(screen.getByRole('button', { name: /reprendre dans commercial/i })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /commencer dans finance/i })).toBeNull()
    } else {
      expect(screen.getByRole('button', { name: /commencer dans finance/i })).toBeInTheDocument()
    }
  })
})
