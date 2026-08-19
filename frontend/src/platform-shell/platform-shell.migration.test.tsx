/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
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

vi.mock('../app-launcher', () => ({
  AppLauncher: () => <button type="button">Launcher</button>,
}))

vi.mock('../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="product-mark">M</span>,
}))

vi.mock('../components/notifications/NotificationBell', () => ({
  default: () => <button type="button" aria-label="Notifications">Notif</button>,
}))

vi.mock('../design-system', async () => {
  const actual = await vi.importActual<typeof import('../design-system')>('../design-system')
  return {
    ...actual,
    getProductById: (id: string) => ({
      id,
      displayName: id === 'salespilot' ? 'SalesPilot' : 'ComptaPilot',
      shortName: id === 'salespilot' ? 'Sales' : 'Compta',
      colors: { primaryColor: id === 'salespilot' ? '#1D4ED8' : '#0B3D2E' },
      branding: {},
      logoMark: '',
    }),
  }
})

vi.mock('../components/layouts/layoutUtils', () => ({
  userInitials: () => 'AL',
}))

vi.mock('../design-system/overlays/manager/overlayLifecycle', () => ({
  closeAllOverlays: vi.fn(),
}))

describe('PlatformShell migration chrome', () => {
  beforeEach(() => cleanup())
  afterEach(() => cleanup())

  it('topbar SalesPilot : mark + launcher + recherche sans faux résultats', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <PlatformShell productId="salespilot" sidebar={<a href="#n">Nav</a>}>
          <div>Sales content</div>
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(screen.getByText('Commercial')).toBeInTheDocument()
    expect(screen.getByText('Moteur SalesPilot')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /launcher/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /rechercher/i }))
    const dialog = screen.getByRole('dialog', { name: /elfis command center/i })
    expect(within(dialog).getByPlaceholderText(/que souhaitez-vous faire/i)).toBeInTheDocument()
    expect(within(dialog).queryByText('F-2026-0142')).not.toBeInTheDocument()
  })

  it('topbar Finance : ProductIndicator domaine', () => {
    render(
      <MemoryRouter>
        <PlatformShell productId="comptapilot">
          <div>Compta content</div>
        </PlatformShell>
      </MemoryRouter>,
    )
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('Moteur ComptaPilot')).toBeInTheDocument()
  })

  it('UserMenu contient Déconnexion', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <PlatformShell productId="salespilot">
          <div />
        </PlatformShell>
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /ada lovelace/i }))
    expect(screen.getByRole('menuitem', { name: /déconnexion/i })).toBeInTheDocument()
  })
})
