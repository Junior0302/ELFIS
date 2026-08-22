/**
 * @vitest-environment jsdom
 *
 * P2.3.1 — Navigation plateforme & identité produit (22 contrôles).
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { PlatformShell } from './index'
import { PlatformBrandLockup } from './PlatformBrandLockup'
import { UserMenu } from './UserMenu'
import { ProductSidebar, ProductNavigationItem } from './ProductNavigation'
import { isPlatformShellPath } from './platformPaths'
import { resolveRuntimeProductFromPath } from '../design-system/themes/resolveRuntimeProductFromPath'
import { HomePlatformSidebar } from '../home/HomePlatformSidebar'
import { getLauncherFooterLinks } from '../app-launcher/launcherModel'
import { navCategories } from '../navModel'

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
      { organization_id: 1, organization_name: 'Acme SAS', role: 'owner', permissions: ['*'] },
    ],
    orgId: 1,
    setOrgId: vi.fn(),
    logout: vi.fn(),
    token: 't',
    loading: false,
    firebaseReady: true,
  }),
}))

vi.mock('../design-system/themes/ProductThemeProvider', () => ({
  useProductTheme: () => ({ currentProductId: 'comptapilot' }),
}))

vi.mock('../app-launcher', () => ({
  AppLauncher: () => <button type="button">Launcher</button>,
}))

vi.mock('../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="product-mark">M</span>,
}))

vi.mock('../components/notifications/NotificationBell', () => ({
  default: () => (
    <button type="button" aria-label="Notifications">
      Notif
    </button>
  ),
}))

vi.mock('../design-system', async () => {
  const actual = await vi.importActual<typeof import('../design-system')>('../design-system')
  return {
    ...actual,
    getProductById: (id: string) => ({
      id,
      displayName: id === 'elfis-core' ? 'ELFIS Core' : id === 'salespilot' ? 'SalesPilot' : 'ComptaPilot',
      shortName: id,
      colors: {
        primaryColor:
          id === 'comptapilot' ? '#0B3D2E' : id === 'salespilot' ? '#1D4ED8' : '#0B1F3A',
      },
      branding: {},
      logoMark: '',
    }),
  }
})

vi.mock('../components/layouts/layoutUtils', () => ({
  userInitials: () => 'AL',
}))

const closeAllOverlays = vi.fn()
vi.mock('../design-system/overlays/manager/overlayLifecycle', () => ({
  closeAllOverlays: (...args: unknown[]) => closeAllOverlays(...args),
}))

describe('P2.3.1 navigation & identity', () => {
  beforeEach(() => {
    cleanup()
    closeAllOverlays.mockClear()
  })
  afterEach(() => cleanup())

  it('1. lockup ELFIS → /home avec aria-label Retour à ELFIS Home', () => {
    render(
      <MemoryRouter>
        <PlatformBrandLockup />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: 'Retour à ELFIS Home' })
    expect(link).toHaveAttribute('href', '/home')
  })

  it('2. clic lockup ferme les overlays (route_change)', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <PlatformBrandLockup />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('link', { name: 'Retour à ELFIS Home' }))
    expect(closeAllOverlays).toHaveBeenCalledWith('route_change')
  })

  it('3. topbar produit expose lockup Home + indicateur produit', () => {
    render(
      <MemoryRouter>
        <PlatformShell productId="comptapilot" sidebar={<div>nav</div>}>
          <div>page</div>
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'Retour à ELFIS Home' })).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.queryByText('Moteur ComptaPilot')).toBeNull()
  })

  it('4. Home Paramètres → /platform/settings (pas /settings Compta)', () => {
    render(
      <MemoryRouter>
        <HomePlatformSidebar />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /paramètres/i })).toHaveAttribute(
      'href',
      '/platform/settings',
    )
  })

  it('5. UserMenu Paramètres ELFIS → /platform/settings', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { expanded: false }))
    expect(screen.getByRole('menuitem', { name: /paramètres elfis/i })).toHaveAttribute(
      'href',
      '/platform/settings',
    )
  })

  it('6. UserMenu ELFIS Home → /home', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { expanded: false }))
    expect(screen.getByRole('menuitem', { name: /elfis home/i })).toHaveAttribute('href', '/home')
  })

  it('7. UserMenu ne pointe plus Préférences vers /settings Compta', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { expanded: false }))
    const prefs = screen.getByRole('menuitem', { name: /^préférences$/i })
    expect(prefs).not.toHaveAttribute('href', '/settings')
  })

  it('8. launcher footer Paramètres → /platform/settings', () => {
    const settings = getLauncherFooterLinks().find((l) => l.id === 'settings')
    expect(settings?.to).toBe('/platform/settings')
  })

  it('9. /platform/settings → thème elfis-core', () => {
    const r = resolveRuntimeProductFromPath('/platform/settings')
    expect(r.productId).toBe('elfis-core')
    expect(r.surface).toBe('platform')
  })

  it('10. /organisation → elfis-core (plus Compta)', () => {
    expect(resolveRuntimeProductFromPath('/organisation').productId).toBe('elfis-core')
  })

  it('11. /settings reste comptapilot (finance)', () => {
    expect(resolveRuntimeProductFromPath('/settings').productId).toBe('comptapilot')
  })

  it('12. /sales/settings → salespilot', () => {
    expect(resolveRuntimeProductFromPath('/sales/settings').productId).toBe('salespilot')
  })

  it('13. isPlatformShellPath couvre Core settings', () => {
    expect(isPlatformShellPath('/platform/settings')).toBe(true)
    expect(isPlatformShellPath('/organisation')).toBe(true)
    expect(isPlatformShellPath('/settings')).toBe(false)
    expect(isPlatformShellPath('/dashboard')).toBe(false)
  })

  it('14. nav Finance Paramètres = métier only (plus org/abo/membres)', () => {
    const params = navCategories.find((c) => c.id === 'parametres')
    expect(params?.to).toBe('/settings')
    const tos = (params?.children ?? []).map((c) => c.to)
    expect(tos).toContain('/settings')
    expect(tos).not.toContain('/organisation')
    expect(tos).not.toContain('/abonnement')
    expect(tos).not.toContain('/compte')
    expect(tos).not.toContain('/platform/organization')
    expect(tos).not.toContain('/platform/members')
    expect(tos).not.toContain('/platform/communications')
  })

  it('15. ProductSidebar partagé sans if productId', () => {
    const src = readFileSync(resolve(__dirname, 'ProductNavigation.tsx'), 'utf8')
    expect(src).not.toMatch(/productId\s*===\s*['"]comptapilot['"]/)
    expect(src).not.toMatch(/productId\s*===\s*['"]salespilot['"]/)
  })

  it('16. CSS Compta soft green — pas fond blanc seul + texte mint clair', () => {
    const css = readFileSync(resolve(__dirname, 'platform-shell.css'), 'utf8')
    expect(css).toMatch(/\.ps-shell--compta \.ps-sidebar--compta/)
    expect(css).toMatch(/--pilot-secondary/)
    expect(css).toMatch(/inset 3px 0 0 var\(--pilot-primary/)
    // Anti-régression : overrides texte foncé sur nav legacy
    expect(css).toMatch(/\.ps-shell--compta \.nav a/)
    expect(css).toMatch(/var\(--pilot-primary,\s*#0b3d2e\)/)
  })

  it('17. Sales conserve accent bleu (pas de leftovers verts forcés)', () => {
    const css = readFileSync(resolve(__dirname, 'platform-shell.css'), 'utf8')
    expect(css).toMatch(/\.ps-shell--sales/)
    expect(css).toMatch(/#60a5fa|#1d4ed8/i)
  })

  it('18. ProductNavigationItem active + aria via NavLink', () => {
    render(
      <MemoryRouter initialEntries={['/sales']}>
        <ProductSidebar label="Nav test">
          <ProductNavigationItem item={{ id: 'x', label: 'Pipeline', to: '/sales', end: true }} />
        </ProductSidebar>
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: 'Pipeline' })
    expect(link).toHaveAttribute('aria-current', 'page')
    expect(link.className).toMatch(/is-active/)
  })

  it('19. logout UserMenu présent', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { expanded: false }))
    expect(screen.getByRole('menuitem', { name: /déconnexion/i })).toBeInTheDocument()
  })

  it('20. launcher présent dans topbar produit', () => {
    render(
      <MemoryRouter>
        <PlatformShell productId="salespilot">
          <div>page</div>
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Launcher' })).toBeInTheDocument()
  })

  it('21. thème : /home ne persiste pas', () => {
    expect(resolveRuntimeProductFromPath('/home').persist).toBe(false)
  })

  it('22. route platform/settings montée (smoke App path)', () => {
    render(
      <MemoryRouter initialEntries={['/platform/settings']}>
        <Routes>
          <Route path="/platform/settings" element={<div>Hub paramètres ELFIS</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Hub paramètres ELFIS')).toBeInTheDocument()
  })
})
