/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ElfisHomePage from './ElfisHomePage'
import { setLastProductId } from './lastProduct'
import { resetUnifiedPlatformUiFlag, setUnifiedPlatformUiEnabled } from '../unified-platform'

vi.mock('../auth', () => ({
  useAuth: () => ({
    user: { first_name: 'Chris', last_name: 'Demo', email: 'chris@elfis.test' },
    memberships: [
      { organization_id: 'org-1', organization_name: 'ELFIS Demo Org', role: 'owner' },
    ],
    orgId: 'org-1',
    token: 'test-token',
    logout: vi.fn(),
  }),
}))

vi.mock('../api', () => ({
  api: {
    listNotifications: vi.fn(() =>
      Promise.resolve({ total: 0, page: 1, page_size: 5, notifications: [] }),
    ),
  },
}))

vi.mock('../sync/SyncProvider', () => ({
  useSync: () => ({
    unreadNotifications: 2,
    mode: 'polling',
    lastTickAt: { notifications: new Date().toISOString() },
    refresh: vi.fn(),
    subscribe: () => () => undefined,
  }),
}))

describe('ElfisHomePage signature V3', () => {
  beforeEach(() => {
    cleanup()
    resetUnifiedPlatformUiFlag()
    setUnifiedPlatformUiEnabled(true)
    try {
      localStorage?.removeItem('elfis_last_product')
      localStorage?.removeItem('elfis_last_product_at')
    } catch {
      /* jsdom */
    }
  })
  afterEach(() => {
    cleanup()
    resetUnifiedPlatformUiFlag()
  })

  it('affiche hero signature, pulse, command, espaces, rail', async () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Cockpit ELFIS')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /bonjour chris/i })).toBeInTheDocument()
    expect(screen.getAllByText(/ELFIS Demo Org/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Aujourd’hui ELFIS a détecté/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /commencer ma journée/i })).toBeInTheDocument()
    expect(document.querySelector('[data-cockpit-visual="orbit"]')).toBeTruthy()
    expect(document.querySelector('[data-cockpit-hero="v3"]')).toBeTruthy()

    expect(screen.getByRole('heading', { name: /résumé journée/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^finance$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^commercial$/i })).toBeInTheDocument()
    expect(screen.getByText(/aucun signal finance aujourd/i)).toBeInTheDocument()

    expect(screen.getByRole('heading', { name: /continuer votre travail/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /vos espaces/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /vos applications/i })).toBeNull()
    expect(screen.getByRole('heading', { name: /^finance$/i })).toBeInTheDocument()

    expect(screen.getByRole('heading', { name: /timeline globale/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /elfis intelligence/i })).toBeInTheDocument()
    expect(screen.getByText(/pas d’ia générative/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /tout traiter/i })).toBeInTheDocument()
    expect(document.querySelector('.cockpit-intel__insights')).toBeTruthy()

    expect(screen.getByRole('heading', { name: /quick actions/i })).toBeInTheDocument()
    expect(screen.getByText('Health Center')).toBeInTheDocument()

    expect(document.querySelector('[data-home-layout="cockpit-signature-v3"]')).toBeTruthy()
    expect(document.querySelector('[data-cockpit-os="signature-v3"]')).toBeTruthy()
    expect(document.querySelector('[data-cockpit-command="v3"]')).toBeTruthy()
    expect(document.querySelector('[data-elfis-page-frame="v1"]')).toBeTruthy()
    expect(document.querySelector('[data-cockpit-timeline="v1"]')).toBeTruthy()

    await waitFor(() => {
      expect(screen.getByText(/synchronisation/i)).toBeInTheDocument()
    })
  })

  it('hiérarchie V3 : command avant continuer, domaines tiles', () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const primary = document.querySelector('[data-home-layout="cockpit-signature-v3"]')
    expect(primary).toBeTruthy()
    const command = primary!.querySelector('[data-cockpit-command="v3"]')
    const continueEl = primary!.querySelector('[data-cockpit-continue="v1"]')
    expect(command).toBeTruthy()
    expect(continueEl).toBeTruthy()
    expect(
      Boolean(command!.compareDocumentPosition(continueEl!) & Node.DOCUMENT_POSITION_FOLLOWING),
    ).toBe(true)

    expect(screen.queryByRole('heading', { name: /vos applications/i })).toBeNull()
    expect(document.querySelectorAll('.cockpit-space__tile').length).toBe(4)
    expect(document.querySelector('.cockpit-hero--signature')).toBeTruthy()
    expect(document.querySelector('.cockpit-system-rail')).toBeTruthy()
    expect(screen.getByText(/départements de l’entreprise/i)).toBeInTheDocument()
  })

  it('branche Continuer votre travail sur lastProduct réel', () => {
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => {
        store[k] = String(v)
      },
      removeItem: (k: string) => {
        delete store[k]
      },
      clear: () => {
        for (const k of Object.keys(store)) delete store[k]
      },
      key: () => null,
      length: 0,
    })
    setLastProductId('salespilot')
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /continuer votre travail/i })).toBeInTheDocument()
    expect(screen.getAllByText('Commercial').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Reprendre').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Ouvrir').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Historique')).toBeInTheDocument()
    vi.unstubAllGlobals()
  })

  it('quick actions pointent vers des routes existantes', () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const links = screen.getAllByRole('link')
    expect(links.some((a) => a.getAttribute('href') === '/facturation/documents/new')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/devis')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/sales/leads')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/deposit')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/work-queue')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/platform/relations')).toBe(true)
  })

  it('n’invente pas de KPI factures / prospects', () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    expect(screen.queryByText(/2 factures/i)).toBeNull()
    expect(screen.queryByText(/3 prospects/i)).toBeNull()
    expect(screen.getByText(/aucun agrégat documents branché/i)).toBeInTheDocument()
  })
})
