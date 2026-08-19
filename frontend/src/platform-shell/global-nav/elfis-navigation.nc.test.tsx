/**
 * @vitest-environment jsdom
 * NC01–NC30 — NAV.CORE.1 architecture menu principal ELFIS
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { OverlayProvider } from '../../design-system'
import { ElfisGlobalNavigation } from './ElfisGlobalNavigation'
import {
  ELFIS_NAV_BACKLOG,
  ELFIS_NAV_BRAND,
  ELFIS_NAVIGATION_CONFIG,
  filterElfisNavSections,
  flattenElfisNavItems,
  getMainNavSections,
  isElfisNavItemActive,
} from './elfisNavigationConfig'
import { PLATFORM_ICON_GLYPHS } from '../../unified-platform/icons/ElfisIconSystem'

const logout = vi.fn()

vi.mock('../../auth', () => ({
  useAuth: () => ({
    logout,
    user: { first_name: 'Chris', last_name: 'Demo' },
    memberships: [
      {
        organization_id: 1,
        organization_name: 'Acme',
        role: 'admin',
        permissions: ['*', 'documents.read', 'users.manage', 'ai.analysis'],
      },
    ],
    orgId: 1,
  }),
}))

vi.mock('../../app-launcher/ProductMark', () => ({
  ProductMark: () => <span data-testid="product-mark">M</span>,
}))

function renderSidebar(opts?: {
  path?: string
  collapsed?: boolean
  onCollapsedChange?: (v: boolean | ((p: boolean) => boolean)) => void
}) {
  return render(
    <MemoryRouter initialEntries={[opts?.path || '/home']}>
      <OverlayProvider>
        <ElfisGlobalNavigation
          mode="sidebar"
          collapsed={opts?.collapsed}
          onCollapsedChange={opts?.onCollapsedChange ?? vi.fn()}
        />
      </OverlayProvider>
    </MemoryRouter>,
  )
}

function renderDrawer(path = '/home') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <OverlayProvider>
        <ElfisGlobalNavigation mode="drawer" open onOpenChange={vi.fn()} />
      </OverlayProvider>
    </MemoryRouter>,
  )
}

const EXPECTED_SECTION_ORDER = ['principal', 'entreprise', 'donnees', 'plateforme', 'outils', 'support']

function getSidebarNav() {
  return screen.getByRole('navigation', { name: /navigation plateforme/i })
}

describe('NAV.CORE.1 NC01–NC30', () => {
  beforeEach(() => {
    cleanup()
    logout.mockClear()
  })
  afterEach(() => cleanup())

  it('NC01 — sections visibles', () => {
    renderSidebar()
    expect(screen.getByRole('heading', { name: /^principal$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^entreprise$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /données partagées/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^plateforme$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^outils$/i })).toBeInTheDocument()
  })

  it('NC02 — ordre des sections', () => {
    const ids = ELFIS_NAVIGATION_CONFIG.map((s) => s.id)
    expect(ids).toEqual(EXPECTED_SECTION_ORDER)
    const orders = ELFIS_NAVIGATION_CONFIG.map((s) => s.order)
    expect(orders).toEqual([...orders].sort((a, b) => a - b))
  })

  it('NC03 — Accueil', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^accueil$/i })).toHaveAttribute(
      'href',
      '/home',
    )
  })

  it('NC04 — Favoris', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^favoris$/i })).toHaveAttribute(
      'href',
      '/home#home-apps',
    )
  })

  it('NC05 — Activité', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^activité$/i })).toHaveAttribute(
      'href',
      '/home#home-activity',
    )
  })

  it('NC06 — Organisation', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^organisation$/i })).toHaveAttribute(
      'href',
      '/platform/organization',
    )
  })

  it('NC07 — Membres et équipes', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /membres et équipes/i })).toHaveAttribute(
      'href',
      '/platform/members',
    )
  })

  it('NC08 — Rôles et permissions', () => {
    renderSidebar()
    expect(
      within(getSidebarNav()).getByRole('link', { name: /rôles et permissions/i }),
    ).toHaveAttribute('href', '/platform/members#roles')
  })

  it('NC09 — Contacts backlog (pas dans le menu)', () => {
    expect(ELFIS_NAV_BACKLOG.some((b) => b.id === 'contacts')).toBe(true)
    expect(flattenElfisNavItems().some((i) => i.id === 'contacts')).toBe(false)
    renderSidebar()
    expect(within(getSidebarNav()).queryByRole('link', { name: /^contacts$/i })).toBeNull()
  })

  it('NC10 — Entreprises backlog', () => {
    expect(ELFIS_NAV_BACKLOG.some((b) => b.id === 'companies')).toBe(true)
    renderSidebar()
    expect(within(getSidebarNav()).queryByRole('link', { name: /^entreprises$/i })).toBeNull()
  })

  it('NC11 — Relations', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^relations$/i })).toHaveAttribute(
      'href',
      '/platform/relations',
    )
  })

  it('NC12 — Documents', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^documents$/i })).toHaveAttribute(
      'href',
      '/platform/documents',
    )
  })

  it('NC13 — Notifications', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^notifications$/i })).toHaveAttribute(
      'href',
      '/notifications',
    )
  })

  it('NC14 — Communications', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^communications$/i })).toHaveAttribute(
      'href',
      '/platform/communications',
    )
  })

  it('NC15 — Paramètres', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /^paramètres$/i })).toHaveAttribute(
      'href',
      '/platform/settings',
    )
  })

  it('NC16 — Intelligence ELFIS', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /intelligence elfis/i })).toHaveAttribute(
      'href',
      '/platform/aura',
    )
    expect(within(getSidebarNav()).queryByRole('link', { name: /^aura$/i })).toBeNull()
  })

  it('NC17 — Centre de santé backlog', () => {
    expect(ELFIS_NAV_BACKLOG.some((b) => b.id === 'health-center')).toBe(true)
    renderSidebar()
    expect(within(getSidebarNav()).queryByRole('link', { name: /centre de santé/i })).toBeNull()
  })

  it('NC18 — Journal backlog', () => {
    expect(ELFIS_NAV_BACKLOG.some((b) => b.id === 'journal')).toBe(true)
    renderSidebar()
    expect(within(getSidebarNav()).queryByRole('link', { name: /^journal$/i })).toBeNull()
  })

  it('NC19 — Recherche globale', () => {
    renderSidebar()
    expect(within(getSidebarNav()).getByRole('link', { name: /recherche globale/i })).toHaveAttribute(
      'href',
      '/search',
    )
  })

  it('NC20 — Aide et support', () => {
    renderSidebar()
    expect(screen.getByRole('link', { name: /aide et support/i })).toHaveAttribute(
      'href',
      '/home#home-status',
    )
  })

  it('NC21 — Déconnexion', () => {
    renderSidebar()
    expect(screen.getByRole('button', { name: /déconnexion/i })).toBeInTheDocument()
  })

  it('NC22 — même config sidebar / drawer', () => {
    const expectedHrefs = flattenElfisNavItems()
      .filter((i) => i.to)
      .map((i) => i.to as string)
    const { unmount, container } = renderSidebar()
    const sidebarRoot = container.querySelector('[data-elfis-nav="sidebar"]')!
    const sidebarHrefs = [...sidebarRoot.querySelectorAll('a')]
      .map((el) => el.getAttribute('href'))
      .filter(Boolean) as string[]
    expect(sidebarHrefs).toEqual(expectedHrefs)
    unmount()
    cleanup()
    renderDrawer()
    const drawerRoot = document.querySelector('[data-elfis-nav="drawer"]')
    expect(drawerRoot).toBeTruthy()
    const drawerHrefs = [...drawerRoot!.querySelectorAll('a')]
      .map((el) => el.getAttribute('href'))
      .filter(Boolean) as string[]
    expect(drawerHrefs).toEqual(expectedHrefs)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(within(screen.getByRole('dialog')).queryByText('ELFIS Core')).toBeNull()
  })

  it('NC23 — pictogrammes mapping', () => {
    const expected: Record<string, string> = {
      home: 'home',
      favorites: 'star',
      activity: 'activity',
      organization: 'building',
      members: 'users',
      roles: 'shield',
      relations: 'network',
      documents: 'file',
      notifications: 'bell',
      communications: 'mail',
      settings: 'settings',
      intelligence: 'sparkles',
      search: 'search',
      help: 'help-circle',
      logout: 'log-out',
    }
    for (const item of flattenElfisNavItems()) {
      expect(item.icon).toBe(expected[item.id])
      expect(PLATFORM_ICON_GLYPHS[item.icon as keyof typeof PLATFORM_ICON_GLYPHS]).toBeTruthy()
    }
  })

  it('NC24 — permissions', () => {
    const denied = filterElfisNavSections(ELFIS_NAVIGATION_CONFIG, () => false)
    const ids = flattenElfisNavItems(denied).map((i) => i.id)
    expect(ids).not.toContain('members')
    expect(ids).not.toContain('roles')
    expect(ids).not.toContain('documents')
    expect(ids).not.toContain('intelligence')
    expect(ids).toContain('home')
    expect(ids).toContain('logout')
  })

  it('NC25 — état actif', () => {
    const docs = flattenElfisNavItems().find((i) => i.id === 'documents')!
    expect(isElfisNavItemActive('/platform/documents', '', docs)).toBe(true)
    expect(isElfisNavItemActive('/platform/organization', '', docs)).toBe(false)
    const roles = flattenElfisNavItems().find((i) => i.id === 'roles')!
    const members = flattenElfisNavItems().find((i) => i.id === 'members')!
    expect(isElfisNavItemActive('/platform/members', 'roles', roles)).toBe(true)
    expect(isElfisNavItemActive('/platform/members', 'roles', members)).toBe(false)
    expect(isElfisNavItemActive('/platform/members', '', members)).toBe(true)
  })

  it('NC25b — un seul item actif sur /home (pathname + hash)', () => {
    const home = flattenElfisNavItems().find((i) => i.id === 'home')!
    const favorites = flattenElfisNavItems().find((i) => i.id === 'favorites')!
    const activity = flattenElfisNavItems().find((i) => i.id === 'activity')!
    const help = flattenElfisNavItems().find((i) => i.id === 'help')!
    const homeLinked = [home, favorites, activity, help]

    const activeOn = (path: string, hash: string) =>
      homeLinked.filter((item) => isElfisNavItemActive(path, hash, item)).map((i) => i.id)

    expect(activeOn('/home', '')).toEqual(['home'])
    expect(activeOn('/home', '#')).toEqual(['home'])
    expect(activeOn('/home', 'home-apps')).toEqual(['favorites'])
    expect(activeOn('/home', '#home-apps')).toEqual(['favorites'])
    expect(activeOn('/home', 'home-activity')).toEqual(['activity'])
    expect(activeOn('/home', 'home-status')).toEqual(['help'])
    expect(activeOn('/home', 'unknown')).toEqual([])
    expect(activeOn('/platform/settings', '')).toEqual([])
  })

  it('NC25c — UI : un seul aria-current sur /home et hashes', () => {
    const cases: { path: string; activeName: RegExp }[] = [
      { path: '/home', activeName: /^accueil$/i },
      { path: '/home#home-apps', activeName: /^favoris$/i },
      { path: '/home#home-activity', activeName: /^activité$/i },
      { path: '/home#home-status', activeName: /aide et support/i },
    ]
    for (const { path, activeName } of cases) {
      cleanup()
      const { container } = renderSidebar({ path })
      const current = container.querySelectorAll('[aria-current="page"]')
      expect(current).toHaveLength(1)
      expect(current[0]).toHaveClass('is-active')
      expect(current[0]).toHaveAccessibleName(activeName)
      expect(container.querySelectorAll('.elfis-gnav__link.is-active')).toHaveLength(1)
    }
  })

  it('NC26 — collapse masque labels et titres', () => {
    renderSidebar({ collapsed: true, onCollapsedChange: vi.fn() })
    expect(screen.queryByRole('heading', { name: /^principal$/i })).toBeNull()
    expect(document.querySelector('.elfis-gnav.is-collapsed')).toBeTruthy()
    expect(document.querySelectorAll('.elfis-gnav__label').length).toBe(0)
  })

  it('NC27 — tooltips collapse', () => {
    renderSidebar({ collapsed: true, onCollapsedChange: vi.fn() })
    const home = screen.getByRole('link', { name: /^accueil$/i })
    expect(home).toHaveAttribute('title', 'Accueil')
  })

  it('NC28 — mobile drawer = même config', () => {
    renderDrawer('/platform/settings')
    const dialog = screen.getByRole('dialog', { name: /^elfis$/i })
    expect(within(dialog).getByRole('heading', { name: /^principal$/i })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /^paramètres$/i })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(getMainNavSections().map((s) => s.id)).toEqual([
      'principal',
      'entreprise',
      'donnees',
      'plateforme',
      'outils',
    ])
  })

  it('NC29 — terminologie UI ELFIS (pas ELFIS Core) + types config', () => {
    renderSidebar()
    expect(screen.getAllByText('ELFIS').length).toBeGreaterThan(0)
    expect(screen.queryByText('ELFIS Core')).toBeNull()
    expect(ELFIS_NAV_BRAND.name).toBe('ELFIS')
    for (const section of ELFIS_NAVIGATION_CONFIG) {
      expect(typeof section.id).toBe('string')
      expect(typeof section.order).toBe('number')
      expect(['main', 'footer']).toContain(section.placement)
      for (const item of section.items) {
        expect(item.id).toBeTruthy()
        expect(item.label).toBeTruthy()
        expect(item.icon).toBeTruthy()
      }
    }
  })

  it('NC30 — collapse toggle + brand footer', async () => {
    const user = userEvent.setup()
    const onCollapsedChange = vi.fn()
    const { container } = renderSidebar({ collapsed: false, onCollapsedChange })
    expect(container.querySelector('.elfis-gnav__brand')?.textContent).toMatch(/ELFIS/)
    expect(container.querySelector('.elfis-gnav__brand')?.textContent).toMatch(/Plateforme/)
    await user.click(screen.getByRole('button', { name: /réduire la navigation/i }))
    expect(onCollapsedChange).toHaveBeenCalled()
  })
})

