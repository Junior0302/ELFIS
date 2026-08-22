/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { OverlayProvider } from '../design-system'
import { PlatformShell } from './index'

vi.mock('../auth', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'demo@elfis.test',
      first_name: 'Ada',
      last_name: 'Lovelace',
    },
    memberships: [
      { organization_id: 1, organization_name: 'Acme SAS', role: 'owner', permissions: ['*'] },
      { organization_id: 2, organization_name: 'Beta SARL', role: 'member', permissions: [] },
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
  useProductTheme: () => ({ currentProductId: 'salespilot' }),
}))

vi.mock('../app-launcher', () => ({
  AppLauncher: ({ compactTrigger }: { compactTrigger?: boolean }) => (
    <button type="button">{compactTrigger ? 'Launcher compact' : 'Launcher'}</button>
  ),
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
      displayName: id === 'elfis-core' ? 'ELFIS Core' : 'SalesPilot',
      shortName: id === 'elfis-core' ? 'ELFIS' : 'Sales',
      colors: { primaryColor: id === 'elfis-core' ? '#0B1F3A' : '#1D4ED8' },
      branding: {},
      logoMark: '',
    }),
  }
})

vi.mock('../components/layouts/layoutUtils', () => ({
  userInitials: () => 'AL',
}))

vi.mock('../design-system/overlays/manager/overlayLifecycle', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../design-system/overlays/manager/overlayLifecycle')>()
  return {
    ...actual,
    closeAllOverlays: vi.fn(),
  }
})

function renderShell() {
  return render(
    <MemoryRouter>
      <OverlayProvider>
        <PlatformShell productId="salespilot" sidebarTitle="Nav" sidebar={<a href="#x">Item</a>}>
          <div>Viewport métier</div>
        </PlatformShell>
      </OverlayProvider>
    </MemoryRouter>,
  )
}

describe('PlatformShell V1', () => {
  beforeEach(() => {
    cleanup()
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
  afterEach(() => cleanup())

  it('affiche ProductIndicator Commercial sans signature moteur', () => {
    renderShell()
    expect(screen.getByRole('link', { name: 'Retour à ELFIS Home' })).toHaveAttribute('href', '/home')
    expect(screen.getByText('Commercial')).toBeInTheDocument()
    expect(screen.queryByText('Moteur SalesPilot')).toBeNull()
  })

  it('ouvre le Command Center depuis la recherche TopBar', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /rechercher/i }))
    const dialog = await screen.findByRole('dialog', { name: /elfis command center/i })
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getAllByText(/Recherchez, naviguez ou lancez une action/i).length).toBeGreaterThan(
      0,
    )
  })

  it('notifications via NotificationBell', () => {
    renderShell()
    expect(screen.getByRole('button', { name: /notifications/i })).toBeInTheDocument()
  })

  it('menu profil — liens et structure', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /ada lovelace/i }))
    expect(screen.getByRole('menuitem', { name: /mon compte/i })).toHaveAttribute('href', '/compte')
    expect(screen.getByRole('menuitem', { name: /paramètres elfis/i })).toHaveAttribute(
      'href',
      '/platform/settings',
    )
    expect(screen.getByRole('menuitem', { name: /déconnexion/i })).toBeInTheDocument()
  })

  it('organization switcher liste les orgs', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /organisation/i }))
    expect(screen.getByRole('option', { name: /acme sas/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /beta sarl/i })).toBeInTheDocument()
  })

  it('viewport contient le children métier', () => {
    renderShell()
    expect(screen.getByText('Viewport métier')).toBeInTheDocument()
    expect(document.getElementById('platform-workspace')).toBeTruthy()
  })
})
