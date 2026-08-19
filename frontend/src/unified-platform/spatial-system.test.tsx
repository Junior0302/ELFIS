/**
 * UX.UNIFY.1.2 — Unified Spatial System USS01–USS40
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ElfisHomePage from '../home/ElfisHomePage'
import SalesDashboardPage from '../pages/sales/SalesDashboardPage'
import {
  ChartCard,
  ElfisDashboardTemplate,
  ElfisMetricCard,
  ElfisPageFrame,
  PLATFORM_CARD_DIMS,
  PLATFORM_PAGE_FRAME_MAX_WIDTH,
  PLATFORM_PAGE_FRAME_PAD,
  PLATFORM_SURFACES,
  ResponsiveChartFrame,
} from './index'
import { ElfisNavItem } from './navigation/NavigationSystem'

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
    getSalesDashboard: vi.fn(() =>
      Promise.resolve({
        summary: {
          open_leads: 1,
          open_opportunities: 1,
          pipeline_value: 1000,
          weighted_pipeline_value: 500,
          won_opportunities: 0,
          lost_opportunities: 0,
          overdue_tasks: 0,
          activities_today: 0,
        },
        pipeline: { pipeline_id: 1, pipeline_name: 'Default', stages: [] },
        recent_opportunities: [],
        activities: { today: [], tomorrow: [], this_week: [] },
        tasks: { overdue: [], today: [], upcoming: [] },
        quick_actions: [],
        generated_at: new Date().toISOString(),
      }),
    ),
    getSalesIntelligence: vi.fn(() => Promise.resolve(null)),
    listNotifications: vi.fn(() =>
      Promise.resolve({ total: 0, page: 1, page_size: 5, notifications: [] }),
    ),
  },
}))

const upCss = readFileSync(resolve(__dirname, 'unified-platform.css'), 'utf8')
const tokensSrc = readFileSync(resolve(__dirname, 'platformTokens.ts'), 'utf8')
const homeCss = readFileSync(resolve(__dirname, '../home/home.css'), 'utf8')
const shellCss = readFileSync(resolve(__dirname, '../platform-shell/platform-shell.css'), 'utf8')

describe('USS — Unified Spatial System', () => {
  beforeEach(() => cleanup())
  afterEach(() => cleanup())

  // ——— Tokens / frame ———
  it('USS01 — PLATFORM_PAGE_FRAME_MAX_WIDTH = 1680px', () => {
    expect(PLATFORM_PAGE_FRAME_MAX_WIDTH).toBe('1680px')
    expect(tokensSrc).toMatch(/PLATFORM_PAGE_FRAME_MAX_WIDTH\s*=\s*'1680px'/)
  })

  it('USS02 — CSS --up-page-max-width 1680px', () => {
    expect(upCss).toMatch(/--up-page-max-width:\s*1680px/)
  })

  it('USS03 — pad inline desktop 32 (space-8)', () => {
    expect(PLATFORM_PAGE_FRAME_PAD.inlineDesktop).toBe('2rem')
    expect(upCss).toMatch(/--up-page-pad-inline:\s*var\(--space-8/)
  })

  it('USS04 — pad laptop / tablet / mobile breakpoints', () => {
    expect(upCss).toMatch(/max-width:\s*1440px[\s\S]*--up-page-pad-inline:\s*var\(--space-6/)
    expect(upCss).toMatch(/max-width:\s*1024px[\s\S]*--up-page-pad-inline:\s*var\(--space-5/)
    expect(upCss).toMatch(/max-width:\s*640px[\s\S]*--up-page-pad-inline:\s*var\(--space-4/)
  })

  it('USS05 — ElfisPageFrame data-page-frame-max 1680', () => {
    const { container } = render(
      <ElfisPageFrame>
        <span>x</span>
      </ElfisPageFrame>,
    )
    const frame = container.querySelector('[data-elfis-page-frame="v1"]')
    expect(frame?.getAttribute('data-page-frame-max')).toBe('1680')
    expect(frame?.classList.contains('up-page-frame--pad-comfortable')).toBe(true)
  })

  it('USS06 — viewport padding 0 sous unified', () => {
    expect(upCss).toMatch(/\.up-shell--unified\s+\.ps-viewport\s*\{[^}]*padding:\s*0/s)
  })

  it('USS07 — interdit max-width local sous frame (dashboard)', () => {
    expect(upCss).toMatch(/\.up-page-frame\s+\.up-dashboard[\s\S]*max-width:\s*none/s)
  })

  // ——— Sidebar navy ———
  it('USS08 — PLATFORM_SURFACES.sidebar navy', () => {
    expect(PLATFORM_SURFACES.sidebar).toBe('#071629')
  })

  it('USS09 — CSS force navy Compta + Sales + Home', () => {
    expect(upCss).toMatch(/\.up-shell--unified[\s\S]*--up-surface-sidebar:\s*var\(--elfis-navy-950,\s*#071629\)/)
    expect(upCss).toMatch(/ps-sidebar--compta/)
    expect(upCss).toMatch(/ps-sidebar--sales/)
    expect(upCss).toMatch(/background:\s*var\(--up-surface-sidebar/)
  })

  it('USS10 — Home n’impose plus 190px sidebar (UI.P1 via product-sidebar)', () => {
    expect(homeCss).not.toMatch(/--ps-sidebar-w:\s*190px/)
    expect(upCss).toMatch(/--ps-sidebar-w:\s*var\(--product-sidebar-current-width\)/)
    expect(shellCss).toMatch(/--product-sidebar-expanded-width:\s*240px/)
  })

  it('USS11 — UI.P1 sidebar 240/56 toujours dans shell', () => {
    expect(shellCss).toMatch(/--product-sidebar-expanded-width:\s*240px/)
    expect(shellCss).toMatch(/--product-sidebar-collapsed-width:\s*56px/)
  })

  // ——— Template sections ———
  it('USS12 — slots primary / secondary / operations / recent-activity', () => {
    const { container } = render(
      <ElfisDashboardTemplate
        dashboardId="probe"
        header={{ title: 'Tableau de bord' }}
        metrics={<div>kpi</div>}
        primaryAnalysis={<div>p</div>}
        secondaryAnalysis={<div>s</div>}
        operations={<div>o</div>}
        recentActivity={<div>a</div>}
      />,
    )
    expect(container.querySelector('[data-dashboard-slot="header"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="metrics"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="primary"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="secondary"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="actions"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="recent-activity"]')).toBeTruthy()
  })

  it('USS13 — recentActivity vide masqué', () => {
    const { container } = render(
      <ElfisDashboardTemplate
        dashboardId="probe"
        header={{ title: 'Tableau de bord' }}
        primaryAnalysis={<div>p</div>}
        recentActivity={null}
      />,
    )
    expect(container.querySelector('[data-dashboard-slot="recent-activity"]')).toBeNull()
  })

  it('USS14 — legacy children+aside 8/4 si pas primary', () => {
    const { container } = render(
      <ElfisDashboardTemplate
        dashboardId="legacy"
        header={{ title: 'Tableau de bord' }}
        aside={<div>rail</div>}
      >
        <div>main</div>
      </ElfisDashboardTemplate>,
    )
    expect(container.querySelector('.up-dashboard__grid.up-grid--cols-12')).toBeTruthy()
    expect(container.querySelector('.up-dashboard__main.up-grid-item--md-8')).toBeTruthy()
    expect(container.querySelector('.up-dashboard__aside.up-grid-item--md-4')).toBeTruthy()
  })

  it('USS15 — gap dashboard token 24 desktop', () => {
    expect(upCss).toMatch(/--up-dashboard-gap:\s*var\(--space-6/)
  })

  // ——— Cards ———
  it('USS16 — MetricCard min-height 132', () => {
    expect(PLATFORM_CARD_DIMS.metricMinHeight).toBe('132px')
    expect(upCss).toMatch(/--up-metric-min-h:\s*132px/)
    expect(upCss).toMatch(/\.up-metric-card[\s\S]*min-height:\s*var\(--up-metric-min-h/s)
  })

  it('USS17 — ChartCard body clamp 300–420', () => {
    expect(PLATFORM_CARD_DIMS.chartBodyMin).toBe('300px')
    expect(PLATFORM_CARD_DIMS.chartBodyMax).toBe('420px')
    expect(upCss).toMatch(/--up-chart-body-min:\s*300px/)
    expect(upCss).toMatch(/--up-chart-body-max:\s*420px/)
  })

  it('USS18 — ChartCard hero 340–480', () => {
    expect(PLATFORM_CARD_DIMS.chartHeroMin).toBe('340px')
    expect(PLATFORM_CARD_DIMS.chartHeroMax).toBe('480px')
    const { container } = render(
      <ChartCard title="Hero" variant="hero">
        <span>c</span>
      </ChartCard>,
    )
    expect(container.querySelector('.up-chart-card--hero')).toBeTruthy()
  })

  it('USS19 — ChartCard weakData', () => {
    const { container } = render(
      <ChartCard title="Weak" weakData>
        <span>should not show</span>
      </ChartCard>,
    )
    expect(container.querySelector('.up-chart-card--weak')).toBeTruthy()
    expect(container.querySelector('[data-chart-weak="1"]')).toBeTruthy()
    expect(screen.getByText(/Historique insuffisant/i)).toBeTruthy()
  })

  it('USS20 — ElfisMetricCard classe up-metric-card', () => {
    const { container } = render(<ElfisMetricCard title="KPI" value="1" />)
    expect(container.querySelector('.up-metric-card')).toBeTruthy()
  })

  it('USS21 — ResponsiveChartFrame data attribute', () => {
    const { container } = render(
      <ResponsiveChartFrame minWidth={0}>{(w) => <span data-w={w}>ok</span>}</ResponsiveChartFrame>,
    )
    expect(container.querySelector('[data-chart-responsive="v1"]')).toBeTruthy()
  })

  // ——— Home ———
  it('USS22 — Home frame + Cockpit ELFIS', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    expect(container.querySelector('[data-elfis-page-frame="v1"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-id="home"]')).toBeTruthy()
    expect(screen.getByText('Cockpit ELFIS')).toBeTruthy()
  })

  it('USS23 — Home primary / secondary / operations slots', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    expect(container.querySelector('[data-dashboard-slot="primary"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="secondary"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="actions"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="metrics"]')).toBeTruthy()
    expect(container.querySelectorAll('.up-dash-band').length).toBeGreaterThanOrEqual(3)
  })

  it('USS24 — Home blind : pas de class layout métier', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const dash = container.querySelector('[data-elfis-dashboard="v1"]')
    expect(dash?.getAttribute('data-blind-template')).toBe('v1')
    expect(dash?.classList.contains('elfis-home')).toBe(false)
    expect(dash?.classList.contains('up-home--unified')).toBe(false)
  })

  // ——— Sales ———
  it('USS25 — Sales frame + Tableau de bord', async () => {
    const { container } = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText('Tableau de bord')
    expect(container.querySelector('[data-elfis-page-frame="v1"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-id="sales"]')).toBeTruthy()
  })

  it('USS26 — Sales primary + secondary slots', async () => {
    const { container } = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText('Tableau de bord')
    expect(container.querySelector('[data-dashboard-slot="primary"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="secondary"]')).toBeTruthy()
    expect(container.querySelector('[data-dashboard-slot="actions"]')).toBeTruthy()
  })

  it('USS27 — Sales blind : pas de class layout métier', async () => {
    const { container } = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText('Tableau de bord')
    const dash = container.querySelector('[data-elfis-dashboard="v1"]')
    expect(dash?.classList.contains('sales-dashboard')).toBe(false)
    expect(dash?.getAttribute('data-blind-template')).toBe('v1')
  })

  // ——— FCC source / CSS ———
  it('USS28 — FCC titre Tableau de bord dans source', () => {
    const fcc = readFileSync(
      resolve(__dirname, '../comptapilot/financial-command-center/FinancialCommandCenter.tsx'),
      'utf8',
    )
    expect(fcc).toMatch(/title:\s*'Tableau de bord'/)
    expect(fcc).toMatch(/primaryAnalysis=/)
    expect(fcc).toMatch(/secondaryAnalysis=/)
    expect(fcc).toMatch(/ResponsiveChartFrame/)
  })

  it('USS29 — FCC composition spans 8+4 / 6+6 / 8+4', () => {
    const fcc = readFileSync(
      resolve(__dirname, '../comptapilot/financial-command-center/FinancialCommandCenter.tsx'),
      'utf8',
    )
    expect(fcc).toMatch(/up-dash-band--primary/)
    expect(fcc).toMatch(/spanMd=\{8\}/)
    expect(fcc).toMatch(/spanMd=\{4\}/)
    expect(fcc).toMatch(/up-dash-band--secondary/)
    expect(fcc).toMatch(/spanMd=\{6\}/)
    expect(fcc).toMatch(/up-dash-band--activity/)
  })

  it('USS30 — FCC chart weak class support', () => {
    expect(upCss).toMatch(/\.up-chart-card--weak/)
    const fcc = readFileSync(
      resolve(__dirname, '../comptapilot/financial-command-center/FinancialCommandCenter.tsx'),
      'utf8',
    )
    expect(fcc).toMatch(/up-chart-card--weak/)
  })

  // ——— Nav depth ———
  it('USS31 — ElfisNavItem submenu depth', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisNavItem
          pathname="/a/b"
          item={{
            id: 'a',
            label: 'Parent',
            href: '/a',
            children: [{ id: 'b', label: 'Child', href: '/a/b' }],
          }}
        />
      </MemoryRouter>,
    )
    expect(container.querySelector('[data-nav-submenu="v1"]')).toBeTruthy()
    expect(container.querySelector('[data-nav-depth="1"]')).toBeTruthy()
  })

  it('USS32 — nav submenu CSS profondeur partagée', () => {
    expect(upCss).toMatch(/\.up-nav-submenu/)
    expect(upCss).toMatch(/\.up-nav-item-wrap--sub/)
  })

  // ——— Density / header ———
  it('USS33 — density comfortable par défaut', () => {
    const { container } = render(
      <ElfisDashboardTemplate header={{ title: 'Tableau de bord' }} primaryAnalysis={<div />} />,
    )
    expect(
      container.querySelector('[data-dashboard-density="comfortable"]'),
    ).toBeTruthy()
  })

  it('USS34 — PageHeader FR Tableau de bord (template)', () => {
    render(
      <ElfisDashboardTemplate header={{ title: 'Tableau de bord' }} primaryAnalysis={<div />} />,
    )
    expect(screen.getByText('Tableau de bord')).toBeTruthy()
  })

  // ——— Docs presence ———
  it('USS35 — docs 26–34 présentes', () => {
    const docs = resolve(__dirname, '../../docs/unified-platform')
    for (const f of [
      '26-spatial-runtime-audit.md',
      '27-spatial-comparative.md',
      '28-sidebar-navy.md',
      '29-page-frame-1680.md',
      '30-dashboard-sections.md',
      '31-card-dimensions.md',
      '32-three-dashboard-compositions.md',
      '33-test-plan-uss.md',
      '34-uss-implementation-report.md',
    ]) {
      expect(readFileSync(resolve(docs, f), 'utf8').length).toBeGreaterThan(40)
    }
  })

  it('USS36 — doc 33 liste USM À tester manuellement', () => {
    const doc = readFileSync(
      resolve(__dirname, '../../docs/unified-platform/33-test-plan-uss.md'),
      'utf8',
    )
    expect(doc).toMatch(/À tester manuellement/)
    expect(doc).toMatch(/USM20/)
  })

  it('USS37 — pad-md alias comfortable', () => {
    expect(upCss).toMatch(/\.up-page-frame--pad-md,\s*\n\.up-page-frame--pad-comfortable/)
  })

  it('USS38 — charts ResizeObserver export', () => {
    expect(typeof ResponsiveChartFrame).toBe('function')
    const charts = readFileSync(
      resolve(__dirname, '../comptapilot/financial-command-center/fccCharts.tsx'),
      'utf8',
    )
    expect(charts).toMatch(/width:\s*widthProp/)
  })

  it('USS39 — Home et Sales partagent frame padding comfortable', async () => {
    const home = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const homePad = home.container
      .querySelector('[data-elfis-page-frame="v1"]')
      ?.getAttribute('data-page-frame-padding')
    home.unmount()

    const sales = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText('Tableau de bord')
    const salesPad = sales.container
      .querySelector('[data-elfis-page-frame="v1"]')
      ?.getAttribute('data-page-frame-padding')
    expect(homePad).toBe('comfortable')
    expect(salesPad).toBe(homePad)
  })

  it('USS40 — GO STOP documenté (pas pages secondaires)', () => {
    const doc = readFileSync(
      resolve(__dirname, '../../docs/unified-platform/34-uss-implementation-report.md'),
      'utf8',
    )
    expect(doc).toMatch(/STOP/)
    expect(doc).toMatch(/Pas de migration pages secondaires/)
    expect(doc).toMatch(/GO \(14 points\)/)
  })
})
