/**
 * @vitest-environment jsdom
 * MB01–MB20 — suppression 2e bouton menu topbar (UI.P2)
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { OverlayProvider } from '../design-system'
import { PlatformShell } from './PlatformShell'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY,
  writeProductSidebarCollapsedPreference,
} from './productSidebarCollapse'
import { useProductSidebarCollapsed } from './useProductSidebarCollapsed'
import { ComptaProductNav } from './ComptaProductNav'

const logout = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'demo@elfis.test', first_name: 'Chris', last_name: 'Demo' },
    memberships: [
      {
        organization_id: 1,
        organization_name: 'Acme',
        role: 'admin',
        permissions: ['*', 'documents.read', 'users.manage', 'ai.analysis'],
      },
    ],
    orgId: 1,
    setOrgId: vi.fn(),
    logout,
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

vi.mock('../design-system/themes/ProductThemeProvider', () => ({
  useProductTheme: () => ({ currentProductId: 'comptapilot' }),
}))

vi.mock('../app-launcher', () => ({
  AppLauncher: () => <button type="button">Applications</button>,
}))

vi.mock('../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="mark">M</span>,
}))

vi.mock('../components/notifications/NotificationBell', () => ({
  default: () => (
    <button type="button" aria-label="Notifications">
      Notif
    </button>
  ),
}))

const css = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), 'platform-shell.css'),
  'utf8',
)

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

function ComptaShellFixture({ path = '/dashboard' }: { path?: string }) {
  const { collapsed, setCollapsed } = useProductSidebarCollapsed()
  return (
    <PlatformShell
      productId="comptapilot"
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
      <div data-testid="page-body">Contenu {path}</div>
    </PlatformShell>
  )
}

function renderShell(
  path = '/dashboard',
  opts?: { productId?: 'comptapilot' | 'salespilot' | 'elfis-core'; withComptaNav?: boolean },
) {
  const productId = opts?.productId ?? 'comptapilot'
  const withComptaNav = opts?.withComptaNav ?? false
  return render(
    <MemoryRouter initialEntries={[path]}>
      <OverlayProvider>
        <Routes>
          <Route
            path="*"
            element={
              withComptaNav ? (
                <ComptaShellFixture path={path} />
              ) : (
                <PlatformShell
                  productId={productId}
                  sidebar={<nav aria-label="Nav produit">Sidebar produit</nav>}
                >
                  <div data-testid="page-body">Contenu {path}</div>
                </PlatformShell>
              )
            }
          />
        </Routes>
      </OverlayProvider>
    </MemoryRouter>,
  )
}

describe('UI.P2 redundant menu button MB01–MB20', () => {
  beforeEach(() => {
    cleanup()
    installMemoryLocalStorage()
    localStorage.clear()
    logout.mockClear()
  })
  afterEach(() => cleanup())

  it('MB01 — un seul hamburger dans la topbar', () => {
    renderShell()
    const topbar = document.querySelector('.ps-topbar')
    expect(topbar).toBeTruthy()
    const burgers = topbar!.querySelectorAll('.ps-burger')
    expect(burgers.length).toBe(1)
    const menuBtns = within(topbar as HTMLElement).getAllByRole('button', {
      name: /menu elfis/i,
    })
    expect(menuBtns.length).toBe(1)
  })

  it('MB02 — bouton global fonctionnel (ouvre le drawer)', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    expect(screen.getByRole('dialog', { name: /^elfis$/i })).toBeInTheDocument()
  })

  it('MB03 — deuxième bouton topbar produit absent du DOM', () => {
    renderShell()
    expect(document.querySelector('.ps-topbar__product-nav')).toBeNull()
    expect(document.querySelector('.ps-product-nav-glyph')).toBeNull()
    expect(css).not.toMatch(/\.ps-topbar__product-nav\s*\{/)
  })

  it('MB04 — topbar left : pas de trou après le hamburger (Apps suit)', () => {
    renderShell()
    const left = document.querySelector('.ps-topbar__left')
    expect(left).toBeTruthy()
    const kids = Array.from(left!.children).filter((el) => el instanceof HTMLElement)
    expect(kids[0]?.classList.contains('ps-topbar__menu')).toBe(true)
    expect(kids[1]?.textContent).toMatch(/applications/i)
  })

  it('MB05 — pas de focus fantôme sur ancien toggle produit', async () => {
    const user = userEvent.setup()
    renderShell()
    const topbar = document.querySelector('.ps-topbar') as HTMLElement
    await user.tab()
    const focused = document.activeElement as HTMLElement | null
    expect(focused?.classList.contains('ps-topbar__menu')).toBe(true)
    expect(focused?.classList.contains('ps-topbar__product-nav')).toBe(false)
    const topbarButtons = within(topbar).getAllByRole('button')
    for (const btn of topbarButtons) {
      expect(btn.classList.contains('ps-topbar__product-nav')).toBe(false)
    }
  })

  it('MB06 — menu global ouvre', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    expect(screen.getByRole('dialog', { name: /^elfis$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /fermer le menu elfis/i })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('MB07 — menu global ferme (Escape)', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: /^elfis$/i })).toBeNull()
    expect(screen.getByRole('button', { name: /ouvrir le menu elfis/i })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  it('MB08 — sidebar produit toujours présente', () => {
    renderShell()
    expect(screen.getByRole('navigation', { name: /nav produit/i })).toBeInTheDocument()
    expect(document.querySelector('.ps-shell--with-sidebar')).toBeTruthy()
  })

  it('MB09 — collapse sidebar interne (UI.P1) fonctionne', async () => {
    const user = userEvent.setup()
    renderShell('/dashboard', { withComptaNav: true })
    const collapse = screen.getByRole('button', { name: /réduire la navigation/i })
    await user.click(collapse)
    expect(document.querySelector('.ps-shell--sidebar-collapsed')).toBeTruthy()
    expect(localStorage.getItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('1')
  })

  it('MB10 — navigation Finance (shell + indicateur)', () => {
    renderShell('/dashboard', { productId: 'comptapilot', withComptaNav: true })
    expect(document.querySelector('[data-product="comptapilot"]')).toBeTruthy()
    expect(document.querySelector('.ps-product__text strong')?.textContent).toBe('Finance')
    expect(screen.queryByText('Moteur ComptaPilot')).toBeNull()
  })

  it('MB11 — shell Finance / home sans 2e hamburger', () => {
    renderShell('/finance', { productId: 'comptapilot' })
    expect(document.querySelectorAll('.ps-topbar .ps-burger').length).toBe(1)
    expect(document.querySelector('.ps-topbar__product-nav')).toBeNull()
  })

  it('MB12 — shell Facturation sans 2e hamburger', () => {
    renderShell('/facturation/documents', { productId: 'comptapilot' })
    expect(document.querySelectorAll('.ps-topbar .ps-burger').length).toBe(1)
    expect(document.querySelector('.ps-topbar__product-nav')).toBeNull()
  })

  it('MB13 — Composer focus masque le contrôle nav produit contenu', () => {
    expect(css).toMatch(
      /\.ps-shell--composer-focus \.ps-shell__open-product-nav[\s\S]*display:\s*none/,
    )
  })

  it('MB14 — tablette/mobile : CSS ouvre nav produit hors topbar', () => {
    expect(css).toMatch(/max-width:\s*900px[\s\S]*\.ps-shell__open-product-nav[\s\S]*display:\s*inline-flex/s)
    expect(css).not.toMatch(/max-width:\s*900px[\s\S]*\.ps-topbar__product-nav/s)
  })

  it('MB15 — mobile : ouverture nav produit via bouton distinct', async () => {
    const user = userEvent.setup()
    renderShell()
    const openProduct = screen.getByRole('button', { name: /ouvrir la navigation produit/i })
    expect(openProduct).toHaveClass('ps-shell__open-product-nav')
    expect(openProduct.querySelector('.ps-burger')).toBeNull()
    await user.click(openProduct)
    expect(document.querySelector('.ps-sidebar--mobile-open')).toBeTruthy()
    expect(screen.getByRole('button', { name: /fermer la navigation produit/i })).toHaveClass(
      'ps-shell__scrim',
    )
  })

  it('MB16 — clavier : Entrée ouvre le menu ELFIS', async () => {
    const user = userEvent.setup()
    renderShell()
    const btn = screen.getByRole('button', { name: /ouvrir le menu elfis/i })
    btn.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('dialog', { name: /^elfis$/i })).toBeInTheDocument()
  })

  it('MB17 — a11y aria-label dynamique Ouvrir/Fermer menu ELFIS', async () => {
    const user = userEvent.setup()
    renderShell()
    expect(screen.getByRole('button', { name: 'Ouvrir le menu ELFIS' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ouvrir le menu ELFIS' }))
    expect(screen.getByRole('button', { name: 'Fermer le menu ELFIS' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Fermer le menu ELFIS' })).toHaveAttribute(
      'aria-controls',
      'elfis-global-navigation',
    )
  })

  it('MB18 — TypeScript : props produit nav retirées de PlatformTopBar', async () => {
    const src = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), 'PlatformTopBar.tsx'),
      'utf8',
    )
    expect(src).not.toMatch(/showProductNavToggle/)
    expect(src).not.toMatch(/ps-topbar__product-nav/)
    expect(src).toMatch(/Fermer le menu ELFIS/)
  })

  it('MB19 — build tokens CSS : pas de styles orphelins product-nav topbar', () => {
    expect(css).not.toMatch(/\.ps-topbar__product-nav/)
    expect(css).not.toMatch(/\.ps-product-nav-glyph/)
    expect(css).toMatch(/\.ps-shell__open-product-nav/)
  })

  it('MB20 — pas de régression SalesPilot / collapse storage', () => {
    writeProductSidebarCollapsedPreference(true)
    renderShell('/sales', { productId: 'salespilot' })
    expect(document.querySelectorAll('.ps-topbar .ps-burger').length).toBe(1)
    expect(document.querySelector('.ps-topbar__product-nav')).toBeNull()
    expect(screen.getByRole('button', { name: /ouvrir le menu elfis/i })).toBeInTheDocument()
    expect(localStorage.getItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('1')
  })
})
