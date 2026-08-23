/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { OverlayProvider } from '../../design-system'
import { PlatformShell } from '../PlatformShell'
import {
  filterGlobalNavItems,
  isGlobalNavItemActive,
  isComptaPilotPath,
  isSalesPilotPath,
  GLOBAL_NAV_ITEMS,
} from './globalNavModel'

const logout = vi.fn()
const closeAllOverlays = vi.fn()

vi.mock('../../auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'demo@elfis.test', first_name: 'Chris', last_name: 'Demo' },
    memberships: [
      {
        organization_id: 1,
        organization_name: 'Acme',
        role: 'admin',
        permissions: ['*', 'documents.read', 'users.manage', 'ai.analysis', 'bank.read'],
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

vi.mock('../../design-system/themes/ProductThemeProvider', () => ({
  useProductTheme: () => ({ currentProductId: 'comptapilot' }),
}))

vi.mock('../../app-launcher', () => ({
  AppLauncher: () => <button type="button">Launcher</button>,
}))

vi.mock('../../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="mark">M</span>,
}))

vi.mock('../../components/notifications/NotificationBell', () => ({
  default: () => <button type="button" aria-label="Notifications">Notif</button>,
}))

vi.mock('../../design-system/overlays/manager/overlayLifecycle', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('../../design-system/overlays/manager/overlayLifecycle')>()
  return {
    ...actual,
    closeAllOverlays: (...args: unknown[]) => closeAllOverlays(...args),
  }
})

function renderAt(path: string, productId: 'elfis-core' | 'comptapilot' | 'salespilot' = 'comptapilot') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <OverlayProvider>
        <Routes>
          <Route
            path="*"
            element={
              <PlatformShell
                productId={productId}
                sidebar={<nav aria-label="Nav produit">Sidebar produit</nav>}
              >
                <div>Contenu {path}</div>
              </PlatformShell>
            }
          />
        </Routes>
      </OverlayProvider>
    </MemoryRouter>,
  )
}

describe('globalNavModel', () => {
  it('détecte routes Compta / Sales', () => {
    expect(isComptaPilotPath('/dashboard')).toBe(true)
    expect(isComptaPilotPath('/platform/documents')).toBe(false)
    expect(isComptaPilotPath('/banque')).toBe(false)
    expect(isComptaPilotPath('/platform/banking')).toBe(false)
    expect(isSalesPilotPath('/sales/pipeline')).toBe(true)
    expect(isSalesPilotPath('/dashboard')).toBe(false)
  })

  it('active item unique cohérent', () => {
    const docs = GLOBAL_NAV_ITEMS.find((i) => i.id === 'documents')!
    expect(isGlobalNavItemActive('/platform/documents', docs)).toBe(true)
    expect(isGlobalNavItemActive('/platform/organization', docs)).toBe(false)
  })

  it('conserve Accueil / logout sans permission', () => {
    const visible = filterGlobalNavItems(GLOBAL_NAV_ITEMS, () => false)
    expect(visible.some((i) => i.id === 'home')).toBe(true)
    expect(visible.some((i) => i.id === 'logout')).toBe(true)
    expect(visible.some((i) => i.id === 'members')).toBe(false)
  })
})

describe('Global navigation menu S1.1.1', () => {
  beforeEach(() => {
    cleanup()
    logout.mockClear()
    closeAllOverlays.mockClear()
  })
  afterEach(() => cleanup())

  it.each([
    ['/home', 'elfis-core' as const],
    ['/dashboard', 'comptapilot' as const],
    ['/sales', 'salespilot' as const],
    ['/platform/documents', 'elfis-core' as const],
  ])('bouton visible sur %s', (path, productId) => {
    renderAt(path, productId)
    const btn = screen.getByRole('button', { name: /ouvrir le menu elfis/i })
    expect(btn).toBeInTheDocument()
    expect(btn).toHaveAttribute('aria-controls', 'elfis-global-navigation')
    expect(btn).toHaveAttribute('aria-expanded', 'false')
  })

  it('clic ouvre le Drawer et ferme les overlays', async () => {
    const user = userEvent.setup()
    renderAt('/dashboard')
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    expect(closeAllOverlays).toHaveBeenCalledWith('programmatic')
    const dialog = screen.getByRole('dialog', { name: /^elfis$/i })
    expect(dialog).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /fermer le menu elfis/i })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(within(dialog).getByRole('navigation', { name: /menu global elfis/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /^accueil$/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /^organisation$/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /membres/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /^relations$/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /^documents$/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /communications/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /intelligence elfis/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /^paramètres$/i })).toBeInTheDocument()
    expect(within(dialog).queryByRole('link', { name: /^comptapilot$/i })).toBeNull()
    expect(within(dialog).queryByRole('link', { name: /^salespilot$/i })).toBeNull()
    expect(within(dialog).queryByText('ELFIS Core')).toBeNull()
  })

  it('Entrée ouvre le menu', async () => {
    const user = userEvent.setup()
    renderAt('/home', 'elfis-core')
    const btn = screen.getByRole('button', { name: /ouvrir le menu elfis/i })
    btn.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('dialog', { name: /^elfis$/i })).toBeInTheDocument()
  })

  it('Espace ouvre le menu', async () => {
    const user = userEvent.setup()
    renderAt('/home', 'elfis-core')
    const btn = screen.getByRole('button', { name: /ouvrir le menu elfis/i })
    btn.focus()
    await user.keyboard(' ')
    expect(screen.getByRole('dialog', { name: /^elfis$/i })).toBeInTheDocument()
  })

  it('Escape ferme le menu', async () => {
    const user = userEvent.setup()
    renderAt('/dashboard')
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    expect(screen.getByRole('dialog', { name: /^elfis$/i })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: /^elfis$/i })).toBeNull()
  })

  it('bouton X ferme le menu', async () => {
    const user = userEvent.setup()
    renderAt('/dashboard')
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    await user.click(screen.getByRole('button', { name: /^fermer$/i }))
    expect(screen.queryByRole('dialog', { name: /^elfis$/i })).toBeNull()
  })

  it('indique Paramètres actif sur /platform/settings', async () => {
    const user = userEvent.setup()
    renderAt('/platform/settings', 'elfis-core')
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    const link = screen.getByRole('link', { name: /^paramètres$/i })
    expect(link).toHaveAttribute('aria-current', 'page')
  })

  it('navigation vers Organisation ferme le drawer', async () => {
    const user = userEvent.setup()
    renderAt('/dashboard')
    await user.click(screen.getByRole('button', { name: /ouvrir le menu elfis/i }))
    await user.click(screen.getByRole('link', { name: /^organisation$/i }))
    expect(screen.queryByRole('dialog', { name: /^elfis$/i })).toBeNull()
    expect(closeAllOverlays).toHaveBeenCalledWith('route_change')
  })

  it('ne remplace pas la sidebar produit', () => {
    renderAt('/dashboard')
    expect(screen.getByRole('navigation', { name: /nav produit/i })).toBeInTheDocument()
    expect(document.querySelector('.ps-topbar__product-nav')).toBeNull()
    expect(screen.getByRole('button', { name: /ouvrir la navigation produit/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ouvrir la navigation produit/i })).toHaveClass(
      'ps-shell__open-product-nav',
    )
  })
})

