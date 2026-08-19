/**
 * F1.3.2.3 — Refresh route persistence RR01–RR40
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { resolveProductPhase } from '../productPhase'
import { locationReturnKey, sanitizeReturnPath } from './returnPath'
import ProductAccessLayout from '../components/layouts/ProductAccessLayout'
import RequireAuth from '../components/RequireAuth'
import type { SubscriptionInfo } from '../api'

vi.mock('../auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../subscriptionContext', () => ({
  useSubscription: vi.fn(),
}))

vi.mock('../home/ElfisHomeLayout', () => ({
  default: () => <div data-testid="elfis-home-layout">home-layout</div>,
}))

vi.mock('../platform-workspace/PlatformWorkspaceLayout', () => ({
  default: () => <div data-testid="platform-layout">platform</div>,
}))

vi.mock('../components/layouts/WorkspaceLayout', () => ({
  default: () => <div data-testid="workspace-layout">workspace</div>,
}))

vi.mock('../components/layouts/SalesWorkspaceLayout', () => ({
  default: () => <div data-testid="sales-layout">sales</div>,
}))

vi.mock('../components/layouts/PublicLayout', () => ({
  default: () => <div data-testid="public-layout">public</div>,
}))

vi.mock('../components/layouts/EnterpriseSetupLayout', () => ({
  default: () => <div data-testid="setup-layout">setup</div>,
}))

import { useAuth } from '../auth'
import { useSubscription } from '../subscriptionContext'

const useAuthMock = vi.mocked(useAuth)
const useSubMock = vi.mocked(useSubscription)

function entitledSub(over: Partial<SubscriptionInfo> = {}): SubscriptionInfo {
  return {
    plan: 'pro',
    status: 'active',
    price_eur: 19,
    configured: true,
    trial_end: null,
    current_period_end: null,
    cancel_at_period_end: false,
    access_granted: true,
    ...over,
  }
}

function LocationProbe({ label }: { label: string }) {
  const loc = useLocation()
  return (
    <div data-testid="loc">
      {label}:{loc.pathname}
      {loc.search}
    </div>
  )
}

function mockAuth(over: Record<string, unknown> = {}) {
  useAuthMock.mockReturnValue({
    token: 't',
    user: {
      id: 1,
      email: 'a@b.com',
      first_name: 'A',
      last_name: 'B',
      status: 'active',
      is_platform_admin: false,
    },
    memberships: [
      {
        membership_id: 1,
        organization_id: 10,
        organization_name: 'Org',
        role: 'owner',
        permissions: ['*'],
        plan: 'pro',
        country: 'FR',
      },
    ],
    orgId: 10,
    loading: false,
    firebaseReady: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    setOrgId: vi.fn(),
    setUser: vi.fn(),
    setMemberships: vi.fn(),
    refreshSession: vi.fn(),
    ...over,
  } as unknown as ReturnType<typeof useAuth>)
}

function mockSub(over: Record<string, unknown> = {}) {
  useSubMock.mockReturnValue({
    subscription: entitledSub(),
    loading: false,
    error: '',
    refresh: vi.fn(),
    setSubscription: vi.fn(),
    checkoutReturnPending: false,
    setCheckoutReturnPending: vi.fn(),
    ...over,
  } as unknown as ReturnType<typeof useSubscription>)
}

function renderProductAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="*" element={<ProductAccessLayout />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  mockAuth()
  mockSub()
})

afterEach(() => {
  cleanup()
})

describe('returnPath helpers — RR01–RR05', () => {
  it('RR01 — sanitizeReturnPath conserve /finance', () => {
    expect(sanitizeReturnPath('/finance')).toBe('/finance')
  })

  it('RR02 — sanitizeReturnPath conserve query', () => {
    expect(sanitizeReturnPath('/facturation/documents/new?type=invoice')).toBe(
      '/facturation/documents/new?type=invoice',
    )
  })

  it('RR03 — refuse /login /register', () => {
    expect(sanitizeReturnPath('/login')).toBe('/home')
    expect(sanitizeReturnPath('/register')).toBe('/home')
  })

  it('RR04 — refuse /welcome', () => {
    expect(sanitizeReturnPath('/welcome')).toBe('/home')
  })

  it('RR05 — locationReturnKey path+search+hash', () => {
    expect(
      locationReturnKey({ pathname: '/finance', search: '?x=1', hash: '#y' }),
    ).toBe('/finance?x=1#y')
  })
})

describe('resolveProductPhase bootstrap — RR06–RR10', () => {
  it('RR06 — loading si subscription null + loading', () => {
    expect(resolveProductPhase(null, { subscriptionLoading: true })).toBe('loading')
  })

  it('RR07 — pas loading si subscription déjà connue', () => {
    expect(resolveProductPhase(entitledSub(), { subscriptionLoading: true })).toBe('entitled')
  })

  it('RR08 — null sans loading → no_entitlement (après bootstrap)', () => {
    expect(resolveProductPhase(null)).toBe('no_entitlement')
  })

  it('RR09 — admin bypass', () => {
    expect(resolveProductPhase(null, { isPlatformAdmin: true })).toBe('entitled')
  })

  it('RR10 — entitled access_granted', () => {
    expect(resolveProductPhase(entitledSub())).toBe('entitled')
  })
})

describe('ProductAccessLayout refresh — RR11–RR25', () => {
  it('RR11 — loading → BootstrapLoadingScreen (pas Home)', () => {
    mockSub({ subscription: null, loading: true })
    renderProductAt('/dashboard')
    expect(screen.getByTestId('bootstrap-loading')).toBeInTheDocument()
    expect(screen.queryByTestId('elfis-home-layout')).not.toBeInTheDocument()
  })

  it('RR12 — /dashboard entitled → workspace (pas Home)', () => {
    renderProductAt('/dashboard')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR13 — /finance entitled → workspace', () => {
    renderProductAt('/finance')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR14 — /facturation/documents entitled → workspace', () => {
    renderProductAt('/facturation/documents')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR15 — /facturation/documents/new?type=invoice → workspace', () => {
    renderProductAt('/facturation/documents/new?type=invoice')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR16 — /accounting/proposals → workspace', () => {
    renderProductAt('/accounting/proposals')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR17 — /platform/relations → platform layout', () => {
    renderProductAt('/platform/relations')
    expect(screen.getByTestId('platform-layout')).toBeInTheDocument()
  })

  it('RR18 — /platform/documents → platform layout', () => {
    renderProductAt('/platform/documents')
    expect(screen.getByTestId('platform-layout')).toBeInTheDocument()
  })

  it('RR19 — /settings → workspace', () => {
    renderProductAt('/settings')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR20 — /home → elfis home layout', () => {
    renderProductAt('/home')
    expect(screen.getByTestId('elfis-home-layout')).toBeInTheDocument()
  })

  it('RR21 — /sales → sales layout', () => {
    renderProductAt('/sales')
    expect(screen.getByTestId('sales-layout')).toBeInTheDocument()
  })

  it('RR22 — erreur abonnement → message + pas Home', () => {
    mockSub({ subscription: null, loading: false, error: 'Réseau indisponible' })
    renderProductAt('/finance')
    expect(screen.getByTestId('subscription-load-error')).toBeInTheDocument()
    expect(screen.getByText(/Réseau indisponible/i)).toBeInTheDocument()
  })

  it('RR23 — org inaccessible → écran explicite', () => {
    mockAuth({ orgId: 999 })
    renderProductAt('/dashboard')
    expect(screen.getByTestId('org-inaccessible')).toBeInTheDocument()
  })

  it('RR24 — no_entitlement → welcome/public (pas Home direct)', async () => {
    mockSub({
      subscription: entitledSub({ access_granted: false, status: 'none' }),
      loading: false,
    })
    renderProductAt('/finance')
    await waitFor(() => {
      expect(screen.getByTestId('public-layout')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('elfis-home-layout')).not.toBeInTheDocument()
    expect(screen.queryByTestId('workspace-layout')).not.toBeInTheDocument()
  })

  it('RR25 — welcome + entitled + from=/finance → /finance', async () => {
    render(
      <MemoryRouter initialEntries={[{ pathname: '/welcome', state: { from: '/finance' } }]}>
        <Routes>
          <Route path="welcome" element={<ProductAccessLayout />} />
          <Route path="finance" element={<LocationProbe label="finance" />} />
          <Route path="home" element={<LocationProbe label="home" />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe('finance:/finance')
    })
  })
})

describe('RequireAuth return path — RR26–RR30', () => {
  it('RR26 — loading auth → bootstrap (pas login/home)', () => {
    mockAuth({ loading: true, user: null })
    render(
      <MemoryRouter initialEntries={['/finance']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="finance" element={<LocationProbe label="ok" />} />
          </Route>
          <Route path="login" element={<LocationProbe label="login" />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('bootstrap-loading')).toBeInTheDocument()
  })

  it('RR27 — unauthenticated → login avec from path+query', async () => {
    mockAuth({ loading: false, user: null, token: null })
    render(
      <MemoryRouter initialEntries={['/finance?tab=cash']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="finance" element={<LocationProbe label="ok" />} />
          </Route>
          <Route path="login" element={<div data-testid="login-from">login</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('login-from')).toBeInTheDocument()
    })
  })

  it('RR28 — authenticated → outlet route demandée', () => {
    mockAuth({ loading: false })
    render(
      <MemoryRouter initialEntries={['/copilote']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="copilote" element={<LocationProbe label="ok" />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('loc').textContent).toBe('ok:/copilote')
  })

  it('RR29 — sanitize refuse strings non-/ ', () => {
    expect(sanitizeReturnPath('https://evil.com')).toBe('/home')
    expect(sanitizeReturnPath(null)).toBe('/home')
  })

  it('RR30 — fallback custom', () => {
    expect(sanitizeReturnPath(undefined, '/dashboard')).toBe('/dashboard')
  })
})

describe('Catch-all / modal semantics — RR31–RR40', () => {
  it('RR31 — routes métier ne sont pas des fallbacks home', () => {
    const routes = [
      '/dashboard',
      '/facturation/documents',
      '/facturation/documents/new',
      '/finance',
      '/accounting/proposals',
      '/platform/relations',
      '/platform/documents',
      '/settings',
      '/copilote',
    ]
    for (const path of routes) {
      cleanup()
      mockAuth()
      mockSub({ subscription: entitledSub(), loading: false })
      renderProductAt(path)
      expect(screen.queryByTestId('elfis-home-layout')).not.toBeInTheDocument()
      expect(screen.queryByTestId('bootstrap-loading')).not.toBeInTheDocument()
    }
  })

  it('RR32 — phase loading ne navigue pas', () => {
    mockSub({ subscription: null, loading: true })
    renderProductAt('/platform/relations')
    expect(screen.getByTestId('bootstrap-loading')).toBeInTheDocument()
  })

  it('RR33 — admin + loading sub → entitled immédiat', () => {
    mockAuth({
      user: {
        id: 1,
        email: 'a@b.com',
        first_name: 'A',
        last_name: 'B',
        status: 'active',
        is_platform_admin: true,
      },
    })
    mockSub({ subscription: null, loading: true })
    renderProductAt('/dashboard')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR34 — welcome sans from → /home quand entitled', async () => {
    render(
      <MemoryRouter initialEntries={['/welcome']}>
        <Routes>
          <Route path="welcome" element={<ProductAccessLayout />} />
          <Route path="home" element={<LocationProbe label="home" />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe('home:/home')
    })
  })

  it('RR35 — onboarding entreprise path → setup layout', () => {
    renderProductAt('/onboarding/entreprise')
    expect(screen.getByTestId('setup-layout')).toBeInTheDocument()
  })

  it('RR36 — compte public path sans entitlement → public layout', () => {
    mockSub({
      subscription: entitledSub({ access_granted: false, status: 'none' }),
    })
    renderProductAt('/compte')
    expect(screen.getByTestId('public-layout')).toBeInTheDocument()
  })

  it('RR37 — abonnement public path', () => {
    mockSub({
      subscription: entitledSub({ access_granted: false, status: 'none' }),
    })
    renderProductAt('/abonnement')
    expect(screen.getByTestId('public-layout')).toBeInTheDocument()
  })

  it('RR38 — modal composer path reste workspace (Documents background)', () => {
    renderProductAt('/facturation/documents/new?type=quote')
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR39 — memberships vides + orgId → pas org-inaccessible', () => {
    mockAuth({ memberships: [], orgId: 10 })
    renderProductAt('/dashboard')
    expect(screen.queryByTestId('org-inaccessible')).not.toBeInTheDocument()
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })

  it('RR40 — erreur sub ignorée pour platform admin', () => {
    mockAuth({
      user: {
        id: 1,
        email: 'a@b.com',
        first_name: 'A',
        last_name: 'B',
        status: 'active',
        is_platform_admin: true,
      },
    })
    mockSub({ subscription: null, loading: false, error: 'down' })
    renderProductAt('/finance')
    expect(screen.queryByTestId('subscription-load-error')).not.toBeInTheDocument()
    expect(screen.getByTestId('workspace-layout')).toBeInTheDocument()
  })
})
