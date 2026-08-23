/**
 * @vitest-environment jsdom
 * UXU01–13 — Unified Platform Vague 1
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  ChartCard,
  ContextualSubNav,
  DomainNav,
  ElfisButton,
  ElfisButtonLink,
  ElfisDashboardTemplate,
  ElfisEmptyState,
  ElfisIcon,
  ElfisMetricCard,
  ElfisPageFrame,
  ElfisPageHeader,
  ElfisTable,
  ElfisUnifiedShell,
  GridItem,
  MotionPage,
  MotionSystem,
  PILOT_ACCENT_EXPECTATIONS,
  PLATFORM_PAGE_FRAME_MAX_WIDTH,
  PLATFORM_SHELL_DIMENSIONS,
  PLATFORM_SPACE,
  PLATFORM_SURFACES,
  PLATFORM_TYPOGRAPHY,
  PageLayout,
  PilotThemeProvider,
  PilotWorkspace,
  PlatformGrid,
  PlatformPageContainer,
  isUnifiedPlatformUiEnabled,
  resetUnifiedPlatformUiFlag,
  resolveElfisIcon,
  resolvePilotTheme,
  setUnifiedPlatformUiEnabled,
  usePilotTheme,
} from './index'
import {
  PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX,
  PRODUCT_SIDEBAR_EXPANDED_WIDTH_PX,
} from '../platform-shell/productSidebarCollapse'

vi.mock('../auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'demo@elfis.test', first_name: 'Ada', last_name: 'Lovelace' },
    memberships: [
      { organization_id: 1, organization_name: 'Acme', role: 'owner', permissions: ['*'] },
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
  default: () => (
    <button type="button" aria-label="Notifications">
      Notif
    </button>
  ),
}))

vi.mock('../design-system/overlays/manager/overlayLifecycle', () => ({
  closeAllOverlays: vi.fn(),
}))

vi.mock('../components/layouts/layoutUtils', () => ({
  userInitials: () => 'AL',
}))

describe('Unified Platform Vague 1', () => {
  beforeEach(() => {
    cleanup()
    resetUnifiedPlatformUiFlag()
  })
  afterEach(() => {
    cleanup()
    resetUnifiedPlatformUiFlag()
  })

  it('UXU01 — ElfisUnifiedShell expose data-platform-shell + up-shell', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisUnifiedShell pilotId="comptapilot" sidebar={<nav>Nav</nav>}>
          <div>Content</div>
        </ElfisUnifiedShell>
      </MemoryRouter>,
    )
    const shell = container.querySelector('[data-platform-shell="v1"]')
    expect(shell).toBeTruthy()
    expect(shell?.classList.contains('up-shell')).toBe(true)
    expect(shell?.classList.contains('up-shell--unified')).toBe(true)
    expect(shell?.getAttribute('data-product')).toBe('comptapilot')
  })

  it('UXU02 — topbar structure menu + brand sur 3 pilots', () => {
    for (const pilotId of ['elfis-core', 'comptapilot', 'salespilot'] as const) {
      cleanup()
      const { container } = render(
        <MemoryRouter>
          <ElfisUnifiedShell
            pilotId={pilotId}
            chrome={{ showProductIndicator: pilotId !== 'elfis-core' }}
            sidebar={<nav>Nav</nav>}
          >
            <div>x</div>
          </ElfisUnifiedShell>
        </MemoryRouter>,
      )
      expect(container.querySelector('.ps-topbar')).toBeTruthy()
      expect(container.querySelector('.ps-topbar__menu')).toBeTruthy()
      expect(container.querySelector('.ps-brand')).toBeTruthy()
      expect(container.querySelectorAll('.ps-topbar__menu').length).toBe(1)
    }
  })

  it('UXU03 — un seul hamburger topbar', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisUnifiedShell pilotId="salespilot" sidebar={<nav>Nav</nav>}>
          <div>x</div>
        </ElfisUnifiedShell>
      </MemoryRouter>,
    )
    expect(container.querySelectorAll('.ps-topbar__menu').length).toBe(1)
    expect(screen.getByLabelText(/menu ELFIS/i)).toBeInTheDocument()
  })

  it('UXU04 — pastille Pilot Compta/Sales, absente si chrome Home', () => {
    const { container: c1 } = render(
      <MemoryRouter>
        <ElfisUnifiedShell pilotId="comptapilot" sidebar={<nav>n</nav>}>
          <div>x</div>
        </ElfisUnifiedShell>
      </MemoryRouter>,
    )
    expect(c1.querySelector('.ps-product')).toBeTruthy()
    cleanup()
    const { container: c2 } = render(
      <MemoryRouter>
        <ElfisUnifiedShell
          pilotId="elfis-core"
          chrome={{ showProductIndicator: false }}
          sidebar={<nav>n</nav>}
        >
          <div>x</div>
        </ElfisUnifiedShell>
      </MemoryRouter>,
    )
    expect(c2.querySelector('.ps-product')).toBeNull()
  })

  it('UXU05/06 — collapse sync classe shell (Compta & Sales)', () => {
    for (const pilotId of ['comptapilot', 'salespilot'] as const) {
      cleanup()
      const { container } = render(
        <MemoryRouter>
          <ElfisUnifiedShell pilotId={pilotId} sidebarCollapsed sidebar={<nav>n</nav>}>
            <div>x</div>
          </ElfisUnifiedShell>
        </MemoryRouter>,
      )
      const shell = container.querySelector('[data-platform-shell="v1"]')
      expect(shell?.classList.contains('ps-shell--sidebar-collapsed')).toBe(true)
      expect(shell?.getAttribute('data-sidebar-collapsed')).toBe('true')
    }
  })

  it('UXU07 — tokens dimensions shell UI.P1', () => {
    expect(PLATFORM_SHELL_DIMENSIONS.sidebarExpanded).toBe('240px')
    expect(PLATFORM_SHELL_DIMENSIONS.sidebarCollapsed).toBe('56px')
    expect(PLATFORM_SHELL_DIMENSIONS.topbarHeight).toBe('64px')
    expect(PRODUCT_SIDEBAR_EXPANDED_WIDTH_PX).toBe(240)
    expect(PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX).toBe(56)
    expect(PLATFORM_SPACE[4]).toBe('1rem')
    expect(PLATFORM_SHELL_DIMENSIONS.pageMaxWidth).toBe('1680px')
    expect(PLATFORM_PAGE_FRAME_MAX_WIDTH).toBe('1680px')
  })

  it('UXU08 — PlatformPageContainer', () => {
    const { container } = render(
      <PlatformPageContainer>
        <p>Page</p>
      </PlatformPageContainer>,
    )
    const el = container.querySelector('[data-platform-page-container="v1"]')
    expect(el).toBeTruthy()
    expect(el?.classList.contains('up-page')).toBe(true)
    expect(el?.classList.contains('up-page--unified')).toBe(true)
    expect(el?.classList.contains('ds-container--xl')).toBe(true)
  })

  it('UXU08b — ElfisPageFrame contrôle largeur 1680', () => {
    const { container } = render(
      <ElfisPageFrame>
        <p>Frame</p>
      </ElfisPageFrame>,
    )
    const el = container.querySelector('[data-elfis-page-frame="v1"]')
    expect(el).toBeTruthy()
    expect(el?.classList.contains('up-page-frame')).toBe(true)
    expect(el?.classList.contains('up-page-frame--pad-comfortable')).toBe(true)
    expect(el?.getAttribute('data-page-frame-padding')).toBe('comfortable')
    expect(el?.getAttribute('data-page-frame-max')).toBe('1680')
  })

  it('UXU09/10 — PlatformGrid 12/8/4 + GridItem', () => {
    const { container, rerender } = render(
      <PlatformGrid columns={12}>
        <GridItem span={4}>A</GridItem>
        <GridItem span={8}>B</GridItem>
      </PlatformGrid>,
    )
    expect(container.querySelector('[data-platform-grid="v1"]')?.getAttribute('data-columns')).toBe(
      '12',
    )
    expect(container.querySelector('.up-grid--cols-12')).toBeTruthy()
    expect(container.querySelector('.up-grid-item--span-4')).toBeTruthy()
    expect(container.querySelector('.up-grid-item--span-8')).toBeTruthy()

    rerender(
      <PlatformGrid columns={8}>
        <GridItem span={4}>A</GridItem>
      </PlatformGrid>,
    )
    expect(container.querySelector('.up-grid--cols-8')).toBeTruthy()

    rerender(
      <PlatformGrid columns={4}>
        <GridItem span={2}>A</GridItem>
      </PlatformGrid>,
    )
    expect(container.querySelector('.up-grid--cols-4')).toBeTruthy()
  })

  it('UXU11 — PilotTheme accents Core / Compta / Sales', () => {
    for (const id of ['elfis-core', 'comptapilot', 'salespilot'] as const) {
      const theme = resolvePilotTheme(id)
      const expected = PILOT_ACCENT_EXPECTATIONS[id]
      expect(theme.primary.toUpperCase()).toBe(expected.primary.toUpperCase())
      expect(theme.accent.toUpperCase()).toBe(expected.accent.toUpperCase())
      expect(theme.shellAccentClass).toMatch(/^ps-shell--/)
    }
  })

  it('UXU12/13 — flag UNIFIED_PLATFORM_UI', () => {
    expect(isUnifiedPlatformUiEnabled()).toBe(true)
    setUnifiedPlatformUiEnabled(false)
    expect(isUnifiedPlatformUiEnabled()).toBe(false)
    const { container } = render(
      <MemoryRouter>
        <ElfisUnifiedShell pilotId="comptapilot">
          <div>x</div>
        </ElfisUnifiedShell>
      </MemoryRouter>,
    )
    expect(container.querySelector('.up-shell--unified')).toBeNull()
    setUnifiedPlatformUiEnabled(true)
    cleanup()
    const { container: c2 } = render(
      <MemoryRouter>
        <ElfisUnifiedShell pilotId="comptapilot">
          <div>x</div>
        </ElfisUnifiedShell>
      </MemoryRouter>,
    )
    expect(c2.querySelector('.up-shell--unified')).toBeTruthy()
  })
})

/**
 * UXU14–60 — Vague 2 primitives + contrats pilote
 */
describe('Unified Platform Vague 2 (UXU14–60)', () => {
  beforeEach(() => {
    cleanup()
    resetUnifiedPlatformUiFlag()
  })
  afterEach(() => {
    cleanup()
    resetUnifiedPlatformUiFlag()
  })

  it('UXU14 — PilotThemeProvider expose data-pilot-theme', () => {
    const { container } = render(
      <PilotThemeProvider pilotId="salespilot">
        <span>child</span>
      </PilotThemeProvider>,
    )
    expect(container.querySelector('[data-pilot-theme="salespilot"]')).toBeTruthy()
  })

  it('UXU15 — usePilotTheme hors provider = fallback core', () => {
    function Probe() {
      const t = usePilotTheme()
      return <span data-testid="pid">{t.pilotId}</span>
    }
    render(<Probe />)
    expect(screen.getByTestId('pid').textContent).toBe('elfis-core')
  })

  it('UXU16 — ElfisIcon résout icône Lucide home', () => {
    const { container } = render(<ElfisIcon id="home" />)
    expect(container.querySelector('svg')).toBeTruthy()
  })

  it('UXU17 — resolveElfisIcon path dashboard SVG', () => {
    const node = resolveElfisIcon('/dashboard')
    expect(node).toBeTruthy()
  })

  it('UXU18 — DomainNav rend sections config', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DomainNav
          pathname="/dashboard"
          config={{
            pilotId: 'comptapilot',
            domainId: 'compta',
            sections: [
              {
                id: 'main',
                label: 'Pilotage',
                items: [{ id: 'dash', label: 'Tableau de bord', href: '/dashboard', exact: true }],
              },
            ],
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Pilotage')).toBeTruthy()
    expect(screen.getByText('Tableau de bord')).toBeTruthy()
  })

  it('UXU19 — ContextualSubNav active', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/sales/pipeline']}>
        <ContextualSubNav
          pathname="/sales/pipeline"
          items={[
            { id: 'd', label: 'Dashboard', href: '/sales', exact: true },
            { id: 'p', label: 'Pipeline', href: '/sales/pipeline' },
          ]}
        />
      </MemoryRouter>,
    )
    expect(container.querySelector('.is-active')?.textContent).toMatch(/pipeline/i)
  })

  it('UXU20 — PageLayout + container', () => {
    const { container } = render(
      <PageLayout header={<span>H</span>}>
        <div>Body</div>
      </PageLayout>,
    )
    expect(container.querySelector('[data-page-layout="v1"]')).toBeTruthy()
    expect(container.querySelector('[data-platform-page-container="v1"]')).toBeTruthy()
  })

  it('UXU21 — ElfisPageHeader meta slot', () => {
    render(
      <ElfisPageHeader title="Titre" description="Desc" meta={<span data-testid="meta">M</span>} />,
    )
    expect(screen.getByText('Titre')).toBeTruthy()
    expect(screen.getByTestId('meta')).toBeTruthy()
  })

  it('UXU22 — ElfisDashboardTemplate structure + ElfisPageFrame parent', () => {
    const { container } = render(
      <ElfisDashboardTemplate
        dashboardId="test"
        header={{ title: 'Dash', eyebrow: 'Pilot' }}
        metrics={<div data-testid="m">KPI</div>}
        strip={<div data-testid="s">Strip</div>}
        actions={<div data-testid="act">Act</div>}
        aside={<div data-testid="a">Side</div>}
      >
        <div data-testid="c">Main</div>
      </ElfisDashboardTemplate>,
    )
    const frame = container.querySelector('[data-elfis-page-frame="v1"]')
    const dash = container.querySelector('[data-elfis-dashboard="v1"]')
    expect(frame).toBeTruthy()
    expect(frame?.contains(dash)).toBe(true)
    expect(dash?.getAttribute('data-dashboard-id')).toBe('test')
    expect(container.querySelector('[data-dashboard-slot="header"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="strip"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="metrics"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="actions"]')).toBeTruthy()
    expect(container.querySelector('.up-dashboard__grid.up-grid--cols-12')).toBeTruthy()
    expect(container.querySelector('.up-dashboard__main.up-grid-item--md-8')).toBeTruthy()
    expect(container.querySelector('.up-dashboard__aside.up-grid-item--md-4')).toBeTruthy()
    expect(screen.getByTestId('m')).toBeTruthy()
    expect(screen.getByTestId('a')).toBeTruthy()
    expect(screen.getByTestId('c')).toBeTruthy()
    expect(screen.getByTestId('s')).toBeTruthy()
    expect(screen.getByTestId('act')).toBeTruthy()
  })

  it('UXU23 — ChartCard empty / ready', () => {
    const { rerender } = render(
      <ChartCard title="CA" empty emptyTitle="Vide">
        <svg />
      </ChartCard>,
    )
    expect(screen.getByText('Vide')).toBeTruthy()
    rerender(
      <ChartCard title="CA">
        <span data-testid="chart">ok</span>
      </ChartCard>,
    )
    expect(screen.getByTestId('chart')).toBeTruthy()
  })

  it('UXU24 — ElfisMetricCard classe up-metric-card', () => {
    const { container } = render(<ElfisMetricCard title="Leads" value="3" />)
    expect(container.querySelector('.up-metric-card')).toBeTruthy()
  })

  it('UXU25 — ElfisButton + ElfisButtonLink', () => {
    render(
      <MemoryRouter>
        <ElfisButton>Go</ElfisButton>
        <ElfisButtonLink to="/sales">Sales</ElfisButtonLink>
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Go' }).classList.contains('up-btn')).toBe(true)
    expect(screen.getByRole('link', { name: 'Sales' }).classList.contains('up-btn')).toBe(true)
  })

  it('UXU26 — ElfisEmptyState', () => {
    render(<ElfisEmptyState title="Rien" description="Vide" />)
    expect(screen.getByText('Rien')).toBeTruthy()
  })

  it('UXU27 — ElfisTable', () => {
    const { container } = render(
      <ElfisTable>
        <tbody>
          <tr>
            <td>1</td>
          </tr>
        </tbody>
      </ElfisTable>,
    )
    expect(container.querySelector('[data-elfis-table="v1"]')).toBeTruthy()
  })

  it('UXU28 — MotionSystem tokens + MotionPage', () => {
    expect(MotionSystem.duration.fast).toBeTruthy()
    const { container } = render(
      <MotionPage>
        <span>x</span>
      </MotionPage>,
    )
    expect(container.querySelector('[data-motion="page-enter"]')).toBeTruthy()
  })

  it('UXU29 — PLATFORM_SURFACES neutres (pas accent Pilot)', () => {
    expect(PLATFORM_SURFACES.page).toMatch(/^#/)
    expect(PLATFORM_SURFACES.card).toBe('#FFFFFF')
  })

  it('UXU30 — PLATFORM_TYPOGRAPHY fonts', () => {
    expect(PLATFORM_TYPOGRAPHY.fontDisplay).toContain('--font-display')
  })

  it('UXU31 — PilotWorkspace enfants', () => {
    const { container } = render(
      <MemoryRouter>
        <PilotWorkspace pilotId="comptapilot" title="Compta" nav={<nav>N</nav>}>
          <div>Content</div>
        </PilotWorkspace>
      </MemoryRouter>,
    )
    expect(container.querySelector('[data-product="comptapilot"]')).toBeTruthy()
  })

  it('UXU32–UXU40 — accents distincts 3 pilots', () => {
    const core = resolvePilotTheme('elfis-core')
    const compta = resolvePilotTheme('comptapilot')
    const sales = resolvePilotTheme('salespilot')
    expect(core.accent).not.toBe(compta.accent)
    expect(compta.accent).not.toBe(sales.accent)
    expect(core.shellAccentClass).toBe('ps-shell--home')
    expect(compta.shellAccentClass).toBe('ps-shell--compta')
    expect(sales.shellAccentClass).toBe('ps-shell--sales')
  })

  it('UXU41–UXU45 — dashboard template sans aside = full width main', () => {
    const { container } = render(
      <ElfisDashboardTemplate header={{ title: 'T' }} contained={false}>
        <div>only</div>
      </ElfisDashboardTemplate>,
    )
    expect(container.querySelector('.up-dashboard__aside')).toBeNull()
    expect(container.querySelector('.up-dashboard__main')).toBeTruthy()
  })

  it('UXU46–UXU50 — ChartCard loading', () => {
    render(
      <ChartCard title="Load" loading>
        <span>hidden</span>
      </ChartCard>,
    )
    expect(screen.getByText(/chargement/i)).toBeTruthy()
  })

  it('UXU51–UXU55 — GridItem spans KPI row pattern', () => {
    const { container } = render(
      <PlatformGrid columns={12}>
        <GridItem span={6} spanMd={4} spanLg={2}>
          A
        </GridItem>
        <GridItem span={6} spanMd={4} spanLg={2}>
          B
        </GridItem>
      </PlatformGrid>,
    )
    expect(container.querySelectorAll('[data-platform-grid-item="v1"]').length).toBe(2)
  })

  it('UXU56–UXU60 — flag reset + surfaces card token', () => {
    setUnifiedPlatformUiEnabled(false)
    resetUnifiedPlatformUiFlag()
    expect(isUnifiedPlatformUiEnabled()).toBe(true)
    expect(PLATFORM_SURFACES.card).toBe('#FFFFFF')
    expect(PLATFORM_SHELL_DIMENSIONS.sidebarExpanded).toBe('240px')
  })

  it('UXU61 — CSS page-frame : max-width 1680px + blind template', () => {
    const css = readFileSync(resolve(__dirname, 'unified-platform.css'), 'utf8')
    expect(css).toMatch(/\.up-page-frame\s*\{[^}]*max-width:\s*var\(--up-page-max-width/s)
    expect(css).toMatch(/--up-page-max-width:\s*1680px/)
    expect(css).not.toMatch(/\.up-page-frame\s*\{[^}]*max-width:\s*(960|1100|1200)px/s)
    expect(css).toMatch(/\[data-blind-template="v1"\]/)
  })
})
