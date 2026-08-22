/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ElfisHomePage from './ElfisHomePage'
import { setLastProductId } from './lastProduct'
import { resetUnifiedPlatformUiFlag, setUnifiedPlatformUiEnabled } from '../unified-platform'
import { WORKSPACE_REGISTRY } from '../workspaces'
import { resolveSpaceSummaries } from './homeSignals'

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

describe('ElfisHomePage platform home V4', () => {
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

  it('affiche header exécutif, reprendre, espaces, activité', async () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Cockpit ELFIS')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /bonjour chris|bonsoir chris/i })).toBeInTheDocument()
    expect(screen.getAllByText(/ELFIS Demo Org/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/mérite votre attention aujourd/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /commencer ma journée/i })).toBeInTheDocument()
    expect(document.querySelector('[data-cockpit-visual="orbit"]')).toBeNull()
    expect(document.querySelector('[data-ph-hero="executive"]')).toBeTruthy()
    expect(screen.getAllByText(/Plateforme opérationnelle|Attention requise/i).length).toBeGreaterThanOrEqual(1)

    expect(screen.getByRole('heading', { name: /à reprendre/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /à surveiller/i })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /retrouvez tous les espaces de votre entreprise/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/accédez à vos métiers depuis un environnement elfis unique/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /vos applications/i })).toBeNull()
    expect(screen.queryByRole('heading', { name: /résumé journée/i })).toBeNull()

    expect(screen.getByRole('heading', { name: /activité récente/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /elfis intelligence/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /actions rapides/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /état observé/i })).toBeInTheDocument()

    expect(document.querySelector('[data-home-layout="platform-home-v4"]')).toBeTruthy()
    expect(document.querySelector('[data-cockpit-os="platform-home-v4"]')).toBeTruthy()
    expect(document.querySelector('[data-elfis-page-frame="v1"]')).toBeTruthy()

    await waitFor(() => {
      expect(screen.getAllByText(/synchronisation/i).length).toBeGreaterThanOrEqual(1)
    })
  })

  it('hiérarchie V4 : reprendre avant espaces', () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const primary = document.querySelector('[data-home-layout="platform-home-v4"]')
    expect(primary).toBeTruthy()
    const continueEl = primary!.querySelector('#home-continue')
    const spacesEl = primary!.querySelector('#home-spaces')
    expect(continueEl).toBeTruthy()
    expect(spacesEl).toBeTruthy()
    expect(
      Boolean(continueEl!.compareDocumentPosition(spacesEl!) & Node.DOCUMENT_POSITION_FOLLOWING),
    ).toBe(true)

    expect(document.querySelectorAll('[data-space-card]').length).toBe(WORKSPACE_REGISTRY.length)
  })

  it('branche À reprendre sur lastProduct réel', () => {
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
    expect(screen.getByRole('heading', { name: /à reprendre/i })).toBeInTheDocument()
    expect(screen.getAllByText('Commercial').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Reprendre').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Historique')).toBeInTheDocument()
    vi.unstubAllGlobals()
  })

  it('quick actions pointent vers des routes existantes avec label espace', () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const links = screen.getAllByRole('link')
    expect(links.some((a) => a.getAttribute('href') === '/facturation/documents/new')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/devis')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/sales/leads')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/platform/documents')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/work-queue')).toBe(true)
    expect(links.some((a) => a.getAttribute('href') === '/platform/relations')).toBe(true)

    const facture = document.querySelector('[data-workspace-label="Finance"]')
    const prospect = document.querySelector('[data-workspace-label="Commercial"]')
    const doc = document.querySelector('[data-workspace-label="Documents"]')
    expect(facture).toBeTruthy()
    expect(prospect).toBeTruthy()
    expect(doc).toBeTruthy()
  })

  it('n’invente pas de KPI factures / prospects', () => {
    render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    expect(screen.queryByText(/2 factures/i)).toBeNull()
    expect(screen.queryByText(/3 prospects/i)).toBeNull()
    expect(screen.queryByText(/aucun agrégat documents branché/i)).toBeNull()
  })

  it('cartes espaces dérivées du WORKSPACE_REGISTRY', () => {
    const spaces = resolveSpaceSummaries(null, null)
    expect(spaces.map((s) => s.id)).toEqual(WORKSPACE_REGISTRY.map((w) => w.id))
    expect(spaces.find((s) => s.id === 'finance')?.accent).toBe('#16A34A')
    expect(spaces.find((s) => s.id === 'commercial')?.accent).toBe('#2563EB')
    expect(spaces.find((s) => s.id === 'documents')?.accent).toBe('#7C3AED')
    expect(spaces.find((s) => s.id === 'documents')?.to).toBe('/platform/documents')
    expect(spaces.find((s) => s.id === 'documents')?.available).toBe(true)
  })
})
