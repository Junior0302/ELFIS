/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import {
  OverlayProvider,
  ProductThemeProvider,
  __resetScrollLockForTests,
} from '../design-system'
import { CommandCenter } from './CommandCenter'
import { clearProductEvents, getProductEvents } from '../productEvents'
import type { ReactNode } from 'react'

vi.mock('../auth', () => ({
  useAuth: () => ({
    token: 't',
    orgId: 1,
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B' },
    memberships: [],
    loading: false,
    firebaseReady: true,
  }),
}))

vi.mock('../api', () => ({
  api: {
    searchElfis: vi.fn().mockResolvedValue({
      items: [
        {
          search_document_id: 'sd-1',
          resource_type: 'customer',
          resource_id: '9',
          title: 'Client Démo',
          subtitle: 'Paris',
          snippet: 'Client',
          action_url: '/clients',
          score: 2,
        },
      ],
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
      execution_time_ms: 1,
    }),
  },
}))

afterEach(() => {
  cleanup()
  __resetScrollLockForTests()
  document.getElementById('elfis-overlay-root')?.remove()
  clearProductEvents()
  try {
    localStorage.removeItem('elfis_command_center_recent')
  } catch {
    /* ignore */
  }
})

function renderCc(ui: ReactNode = <CommandCenter />, initialPath = '/home') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ProductThemeProvider
        initialProductId="comptapilot"
        persist={false}
        applyToDom={false}
        resolveFromPath={false}
      >
        <OverlayProvider>
          <Routes>
            <Route path="*" element={ui} />
          </Routes>
        </OverlayProvider>
      </ProductThemeProvider>
    </MemoryRouter>,
  )
}

describe('Command Center V1 integration', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }),
    })
  })

  it('ouvre depuis le trigger TopBar', async () => {
    const user = userEvent.setup()
    renderCc()
    await user.click(screen.getByRole('button', { name: /rechercher/i }))
    expect(await screen.findByRole('dialog', { name: /elfis command center/i })).toBeInTheDocument()
    expect(screen.getAllByText('ELFIS Command Center').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Recherchez, naviguez ou lancez une action/i).length).toBeGreaterThan(0)
  })

  it('raccourci Ctrl+K ouvre le Command Center', async () => {
    const user = userEvent.setup()
    renderCc()
    await user.keyboard('{Control>}k{/Control}')
    expect(await screen.findByRole('dialog', { name: /elfis command center/i })).toBeInTheDocument()
    expect(getProductEvents().some((e) => e.name === 'command_center.open')).toBe(true)
  })

  it('affiche applications et navigation au repos', async () => {
    const user = userEvent.setup()
    renderCc()
    await user.click(screen.getByRole('button', { name: /rechercher/i }))
    expect(await screen.findByText('Applications')).toBeInTheDocument()
    expect(screen.getByText('Navigation')).toBeInTheDocument()
    expect(screen.getByText('ComptaPilot')).toBeInTheDocument()
    expect(screen.getByText('Accueil')).toBeInTheDocument()
  })

  it('mode commande > nouvelle facture', async () => {
    const user = userEvent.setup()
    renderCc()
    await user.click(screen.getByRole('button', { name: /rechercher/i }))
    const input = await screen.findByRole('combobox', { name: /recherche ou commande/i })
    await user.clear(input)
    await user.type(input, '> nouvelle facture')
    expect(await screen.findByText('Mode commande')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Nouvelle facture/i })).toBeInTheDocument()
  })

  it('branche Search Engine V1 pour une requête', async () => {
    const user = userEvent.setup()
    const { api } = await import('../api')
    renderCc()
    await user.click(screen.getByRole('button', { name: /rechercher/i }))
    const input = await screen.findByRole('combobox', { name: /recherche ou commande/i })
    await user.type(input, 'démo')
    await waitFor(() => {
      expect(api.searchElfis).toHaveBeenCalled()
    })
    expect(await screen.findByText('Client Démo')).toBeInTheDocument()
    expect(screen.getByText('Clients')).toBeInTheDocument()
  })

  it('ferme via Escape et émet close', async () => {
    const user = userEvent.setup()
    renderCc()
    const trigger = screen.getByRole('button', { name: /rechercher/i })
    await user.click(trigger)
    expect(await screen.findByRole('dialog', { name: /elfis command center/i })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /elfis command center/i })).toBeNull()
    })
    expect(getProductEvents().some((e) => e.name === 'command_center.close')).toBe(true)
  })
})
