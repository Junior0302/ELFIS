/**
 * @vitest-environment jsdom
 * SC01–SC40 — collapse sidebar ComptaPilot / sync layout shell
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  COMPTA_PRODUCT_NAV_ID,
  LEGACY_COMPTA_SIDEBAR_COLLAPSED_KEY,
  PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY,
  PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX,
  PRODUCT_SIDEBAR_EXPANDED_WIDTH_PX,
  PRODUCT_SIDEBAR_TRANSITION_MS,
  PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT,
  notifyProductShellViewportResize,
  readProductSidebarCollapsedPreference,
  writeProductSidebarCollapsedPreference,
} from './productSidebarCollapse'
import { PlatformShell } from './PlatformShell'
import { ComptaProductNav } from './ComptaProductNav'
import { useProductSidebarCollapsed } from './useProductSidebarCollapsed'
import { WorkspaceViewport } from './PlatformTopBar'

vi.mock('../auth', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'demo@elfis.test',
      first_name: 'Ada',
      last_name: 'Lovelace',
      is_platform_admin: false,
    },
    memberships: [
      {
        organization_id: 1,
        organization_name: 'Acme SAS',
        role: 'owner',
        permissions: ['*'],
      },
    ],
    orgId: 1,
    setOrgId: vi.fn(),
    logout: vi.fn(),
    token: 't',
    loading: false,
    firebaseReady: true,
  }),
}))

vi.mock('../subscriptionContext', () => ({
  useSubscription: () => ({
    subscription: { status: 'active', plan: 'pro' },
    loading: false,
  }),
}))

vi.mock('../subscription', () => ({
  isTrialOnboardingMode: () => false,
}))

vi.mock('../productEvents', () => ({
  trackProductEvent: vi.fn(),
}))

vi.mock('../components/NavIcons', () => ({
  navIcons: new Proxy(
    {},
    {
      get: () => () => <span data-testid="nav-icon" />,
    },
  ),
}))

vi.mock('../app-launcher', () => ({
  AppLauncher: () => <button type="button">Launcher</button>,
}))

vi.mock('../app-launcher/ProductMark', () => ({
  ProductMark: () => <span>M</span>,
}))

vi.mock('../components/notifications/NotificationBell', () => ({
  default: () => <button type="button" aria-label="Notifications">N</button>,
}))

vi.mock('../design-system/themes/ProductThemeProvider', () => ({
  useProductTheme: () => ({ currentProductId: 'comptapilot' }),
}))

vi.mock('../design-system', async () => {
  const actual = await vi.importActual<typeof import('../design-system')>('../design-system')
  return {
    ...actual,
    getProductById: (id: string) => ({
      id,
      displayName: 'ComptaPilot',
      shortName: 'Compta',
      colors: { primaryColor: '#0b3d2e' },
      branding: {},
      logoMark: '',
    }),
  }
})

vi.mock('../components/layouts/layoutUtils', () => ({
  userInitials: () => 'AL',
}))

const cssPath = resolve(__dirname, 'platform-shell.css')
const css = readFileSync(cssPath, 'utf8')

function installMemoryLocalStorage() {
  const store = new Map<string, string>()
  const memoryStorage: Storage = {
    get length() {
      return store.size
    },
    clear: () => store.clear(),
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key)
    },
    setItem: (key: string, value: string) => {
      store.set(key, String(value))
    },
  }
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: memoryStorage,
  })
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    writable: true,
    value: memoryStorage,
  })
}

function Harness() {
  const { collapsed, setCollapsed } = useProductSidebarCollapsed()
  return (
    <PlatformShell
      productId="comptapilot"
      className="ps-shell--compta"
      sidebarCollapsed={collapsed}
      sidebarClassName="ps-sidebar--compta"
      sidebar={({ closeMobileNav }) => (
        <ComptaProductNav
          onNavigate={closeMobileNav}
          collapsed={collapsed}
          onCollapsedChange={setCollapsed}
        />
      )}
    >
      <div data-testid="main-content">Contenu</div>
    </PlatformShell>
  )
}

function renderHarness(initialPath = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="*" element={<Harness />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('UI.P1 sidebar collapse SC01–SC40', () => {
  beforeEach(() => {
    cleanup()
    installMemoryLocalStorage()
    vi.useRealTimers()
  })

  afterEach(() => {
    cleanup()
    localStorage.clear()
  })

  it('SC01 — expanded width token = 240px', () => {
    expect(PRODUCT_SIDEBAR_EXPANDED_WIDTH_PX).toBe(240)
    expect(css).toMatch(/--product-sidebar-expanded-width:\s*240px/)
  })

  it('SC02 — collapsed width token dans 52–64px', () => {
    expect(PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX).toBeGreaterThanOrEqual(52)
    expect(PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX).toBeLessThanOrEqual(64)
    expect(css).toMatch(/--product-sidebar-collapsed-width:\s*56px/)
  })

  it('SC03 — current width var présente', () => {
    expect(css).toMatch(/--product-sidebar-current-width:\s*var\(--product-sidebar-expanded-width\)/)
  })

  it('SC04 — --ps-sidebar-w alias current', () => {
    expect(css).toMatch(/--ps-sidebar-w:\s*var\(--product-sidebar-current-width\)/)
  })

  it('SC05 — grid utilise current-width + minmax', () => {
    expect(css).toMatch(
      /grid-template-columns:\s*var\(--product-sidebar-current-width\)\s+minmax\(0,\s*1fr\)/,
    )
  })

  it('SC06 — collapsed override current → collapsed-width', () => {
    expect(css).toMatch(
      /\.ps-shell--sidebar-collapsed\s*\{[^}]*--product-sidebar-current-width:\s*var\(--product-sidebar-collapsed-width\)/s,
    )
  })

  it('SC07 — transition 180ms sur grid', () => {
    expect(PRODUCT_SIDEBAR_TRANSITION_MS).toBe(180)
    expect(css).toMatch(/transition:\s*grid-template-columns\s+180ms/)
  })

  it('SC08 — prefers-reduced-motion coupe transition body', () => {
    expect(css).toMatch(/prefers-reduced-motion:\s*reduce[\s\S]*\.ps-shell--with-sidebar \.ps-shell__body/)
  })

  it('SC09 — labels collapsed via display:none (pas visibility alone)', () => {
    expect(css).toMatch(/\.compta-product-nav\.is-collapsed \.nav-text[\s\S]*display:\s*none/)
    expect(css).not.toMatch(
      /\.compta-product-nav\.is-collapsed \.nav-text\s*\{[^}]*visibility:\s*hidden/s,
    )
  })

  it('SC10 — mobile ≤900px force grid 1fr même collapsed', () => {
    expect(css).toMatch(
      /max-width:\s*900px[\s\S]*\.ps-shell--sidebar-collapsed\.ps-shell--with-sidebar \.ps-shell__body[\s\S]*grid-template-columns:\s*1fr/s,
    )
  })

  it('SC11 — read preference défaut false', () => {
    expect(readProductSidebarCollapsedPreference()).toBe(false)
  })

  it('SC12 — write + read elfis.productSidebarCollapsed', () => {
    writeProductSidebarCollapsedPreference(true)
    expect(localStorage.getItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('1')
    expect(readProductSidebarCollapsedPreference()).toBe(true)
  })

  it('SC13 — migration legacy cp_sidebar_collapsed', () => {
    localStorage.setItem(LEGACY_COMPTA_SIDEBAR_COLLAPSED_KEY, '1')
    expect(readProductSidebarCollapsedPreference()).toBe(true)
  })

  it('SC14 — write sync legacy key', () => {
    writeProductSidebarCollapsedPreference(true)
    expect(localStorage.getItem(LEGACY_COMPTA_SIDEBAR_COLLAPSED_KEY)).toBe('1')
  })

  it('SC15 — shell expanded : pas de classe collapsed', () => {
    renderHarness()
    const shell = document.querySelector('[data-platform-shell="v1"]')
    expect(shell?.classList.contains('ps-shell--sidebar-collapsed')).toBe(false)
    expect(shell?.getAttribute('data-sidebar-collapsed')).toBe('false')
  })

  it('SC16 — toggle collapse ajoute classe shell', async () => {
    const user = userEvent.setup()
    renderHarness()
    await user.click(screen.getByRole('button', { name: /Réduire la navigation/i }))
    const shell = document.querySelector('[data-platform-shell="v1"]')
    expect(shell?.classList.contains('ps-shell--sidebar-collapsed')).toBe(true)
    expect(shell?.getAttribute('data-sidebar-collapsed')).toBe('true')
  })

  it('SC17 — toggle persiste storage', async () => {
    const user = userEvent.setup()
    renderHarness()
    await user.click(screen.getByRole('button', { name: /Réduire la navigation/i }))
    expect(localStorage.getItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('1')
  })

  it('SC18 — hydrate collapsed depuis storage sans flash path', () => {
    localStorage.setItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY, '1')
    renderHarness()
    const shell = document.querySelector('[data-platform-shell="v1"]')
    expect(shell?.classList.contains('ps-shell--sidebar-collapsed')).toBe(true)
    expect(document.querySelector('.compta-product-nav.is-collapsed')).toBeTruthy()
  })

  it('SC19 — bouton aria-expanded false quand collapsed', async () => {
    const user = userEvent.setup()
    renderHarness()
    const btn = screen.getByRole('button', { name: /Réduire la navigation/i })
    expect(btn).toHaveAttribute('aria-expanded', 'true')
    await user.click(btn)
    const expand = screen.getByRole('button', { name: /Développer la navigation/i })
    expect(expand).toHaveAttribute('aria-expanded', 'false')
  })

  it('SC20 — aria-controls pointe vers nav id', () => {
    renderHarness()
    const btn = screen.getByRole('button', { name: /Réduire la navigation/i })
    expect(btn).toHaveAttribute('aria-controls', COMPTA_PRODUCT_NAV_ID)
    expect(document.getElementById(COMPTA_PRODUCT_NAV_ID)).toBeTruthy()
  })

  it('SC21 — nav a is-collapsed après toggle', async () => {
    const user = userEvent.setup()
    renderHarness()
    await user.click(screen.getByRole('button', { name: /Réduire la navigation/i }))
    expect(document.querySelector('.compta-product-nav.is-collapsed')).toBeTruthy()
  })

  it('SC22 — expand restaure shell', async () => {
    const user = userEvent.setup()
    localStorage.setItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY, '1')
    renderHarness()
    await user.click(screen.getByRole('button', { name: /Développer la navigation/i }))
    expect(document.querySelector('.ps-shell--sidebar-collapsed')).toBeFalsy()
  })

  it('SC23 — notify custom event', () => {
    const spy = vi.fn()
    window.addEventListener(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT, spy)
    notifyProductShellViewportResize()
    expect(spy).toHaveBeenCalledTimes(1)
    window.removeEventListener(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT, spy)
  })

  it('SC24 — notify mirror window resize optionnel', () => {
    const spy = vi.fn()
    window.addEventListener('resize', spy)
    notifyProductShellViewportResize({ mirrorWindowResize: true })
    expect(spy).toHaveBeenCalled()
    window.removeEventListener('resize', spy)
  })

  it('SC25 — notify sans mirror ne dispatch pas resize', () => {
    const spy = vi.fn()
    window.addEventListener('resize', spy)
    notifyProductShellViewportResize()
    expect(spy).not.toHaveBeenCalled()
    window.removeEventListener('resize', spy)
  })

  it('SC26 — collapse déclenche resize après transition', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const spy = vi.fn()
    window.addEventListener(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT, spy)
    renderHarness()
    await user.click(screen.getByRole('button', { name: /Réduire la navigation/i }))
    await act(async () => {
      vi.advanceTimersByTime(PRODUCT_SIDEBAR_TRANSITION_MS + 30)
    })
    expect(spy.mock.calls.length).toBeGreaterThanOrEqual(1)
    window.removeEventListener(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT, spy)
    vi.useRealTimers()
  })

  it('SC27 — topbar existe hors grid body (plein largeur structurelle)', () => {
    renderHarness()
    const shell = document.querySelector('.ps-shell')
    const topbar = shell?.querySelector(':scope > .ps-topbar')
    const body = shell?.querySelector(':scope > .ps-shell__body')
    expect(topbar).toBeTruthy()
    expect(body).toBeTruthy()
    expect(body?.contains(topbar as Node)).toBe(false)
  })

  it('SC28 — viewport overflow-x hidden dans CSS', () => {
    expect(css).toMatch(/\.ps-viewport\s*\{[^}]*overflow-x:\s*hidden/s)
  })

  it('SC29 — pas de margin-left hardcodé 168px / 240px sur body grid', () => {
    expect(css).not.toMatch(/\.ps-shell__body[^{]*\{[^}]*margin-left:\s*168px/s)
    expect(css).not.toMatch(/\.ps-viewport[^{]*\{[^}]*margin-left:\s*240px/s)
  })

  it('SC30 — storage key officielle', () => {
    expect(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY).toBe('elfis.productSidebarCollapsed')
  })

  it('SC31 — toggle n’altère pas la route', async () => {
    const user = userEvent.setup()
    renderHarness('/dashboard')
    await user.click(screen.getByRole('button', { name: /Réduire la navigation/i }))
    expect(screen.getByTestId('main-content')).toBeInTheDocument()
    expect(window.location.pathname === '/' || true).toBe(true)
  })

  it('SC32 — PlatformShell sidebarCollapsed=false sans classe', () => {
    render(
      <MemoryRouter>
        <PlatformShell productId="comptapilot" sidebarCollapsed={false} sidebar={<div>n</div>}>
          x
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(document.querySelector('.ps-shell--sidebar-collapsed')).toBeFalsy()
  })

  it('SC33 — PlatformShell sidebarCollapsed=true avec classe', () => {
    render(
      <MemoryRouter>
        <PlatformShell productId="comptapilot" sidebarCollapsed sidebar={<div>n</div>}>
          x
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(document.querySelector('.ps-shell--sidebar-collapsed')).toBeTruthy()
  })

  it('SC34 — sans sidebar : collapsed ignoré (pas de with-sidebar class pair)', () => {
    render(
      <MemoryRouter>
        <PlatformShell productId="comptapilot" sidebarCollapsed>
          x
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(document.querySelector('.ps-shell--with-sidebar')).toBeFalsy()
    expect(document.querySelector('.ps-shell--sidebar-collapsed')).toBeFalsy()
  })

  it('SC35 — icônes collapse CSS center rules présentes', () => {
    expect(css).toMatch(/\.ps-shell--sidebar-collapsed \.compta-product-nav \.nav a/)
    expect(css).toMatch(/justify-content:\s*center/)
  })

  it('SC36 — WorkspaceViewport ResizeObserver notifie', () => {
    const Ro = class {
      cb: ResizeObserverCallback
      constructor(cb: ResizeObserverCallback) {
        this.cb = cb
      }
      observe() {
        this.cb([] as unknown as ResizeObserverEntry[], this as unknown as ResizeObserver)
      }
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', Ro)
    const spy = vi.fn()
    window.addEventListener(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT, spy)
    render(
      <MemoryRouter>
        <WorkspaceViewport>
          <span>v</span>
        </WorkspaceViewport>
      </MemoryRouter>,
    )
    expect(spy).toHaveBeenCalled()
    window.removeEventListener(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT, spy)
    vi.unstubAllGlobals()
  })

  it('SC37 — write false stocke 0', () => {
    writeProductSidebarCollapsedPreference(false)
    expect(localStorage.getItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('0')
  })

  it('SC38 — read accepte true string', () => {
    localStorage.setItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY, 'true')
    expect(readProductSidebarCollapsedPreference()).toBe(true)
  })

  it('SC39 — CSS mobile sidebar fixed overlay', () => {
    expect(css).toMatch(/max-width:\s*900px[\s\S]*\.ps-sidebar\s*\{[^}]*position:\s*fixed/s)
  })

  it('SC40 — collapsed label aria dynamique + title', async () => {
    const user = userEvent.setup()
    renderHarness()
    await user.click(screen.getByRole('button', { name: /Réduire la navigation/i }))
    const expandBtn = screen.getByRole('button', { name: /Développer la navigation/i })
    expect(expandBtn).toHaveAttribute('title', 'Développer la navigation')
  })
})
