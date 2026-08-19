/**
 * Blind template identity — Home / FCC / Sales indiscernables sans contenu.
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
  ElfisDashboardTemplate,
  sanitizeDashboardClassName,
} from './index'

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

const LAYOUT_ID_CLASSES = [
  'elfis-home',
  'elfis-home--hybrid',
  'up-home--unified',
  'fcc',
  'up-fcc--unified',
  'sales-dashboard',
  'up-sales-dash--unified',
]

function layoutFingerprint(container: HTMLElement) {
  const frame = container.querySelector('[data-elfis-page-frame="v1"]')
  const dash = container.querySelector('[data-elfis-dashboard="v1"]')
  const slots = [
    'header',
    'metrics',
    'primary',
    'secondary',
    'actions',
  ].map((s) => Boolean(container.querySelector(`[data-dashboard-slot="${s}"]`)))
  return {
    frame: Boolean(frame),
    framePad: frame?.getAttribute('data-page-frame-padding'),
    frameMax: frame?.getAttribute('data-page-frame-max'),
    blind: dash?.getAttribute('data-blind-template'),
    density: dash?.getAttribute('data-dashboard-density'),
    className: dash?.className ?? '',
    slots,
  }
}

describe('Blind template identity', () => {
  beforeEach(() => cleanup())
  afterEach(() => cleanup())

  it('BT01 — sanitize retire classes layout métier', () => {
    expect(
      sanitizeDashboardClassName(
        'elfis-home fcc sales-dashboard up-home--unified keep-me',
      ),
    ).toBe('keep-me')
    expect(sanitizeDashboardClassName('fcc up-fcc--unified')).toBeUndefined()
  })

  it('BT02 — Home : frame + blind template, pas de class layout métier', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const fp = layoutFingerprint(container)
    expect(fp.frame).toBe(true)
    expect(fp.blind).toBe('v1')
    expect(fp.framePad).toBe('comfortable')
    expect(fp.frameMax).toBe('1680')
    expect(fp.density).toBe('comfortable')
    expect(fp.slots.every(Boolean)).toBe(true)
    for (const c of LAYOUT_ID_CLASSES) {
      expect(fp.className.split(/\s+/)).not.toContain(c)
    }
  })

  it('BT03 — Sales : même empreinte layout que Home', async () => {
    const home = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const homeFp = layoutFingerprint(home.container)
    home.unmount()

    const sales = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText('Tableau de bord')
    const salesFp = layoutFingerprint(sales.container)
    expect(salesFp.frame).toBe(homeFp.frame)
    expect(salesFp.blind).toBe(homeFp.blind)
    expect(salesFp.framePad).toBe(homeFp.framePad)
    expect(salesFp.frameMax).toBe(homeFp.frameMax)
    expect(salesFp.density).toBe(homeFp.density)
    expect(salesFp.slots).toEqual(homeFp.slots)
    for (const c of LAYOUT_ID_CLASSES) {
      expect(salesFp.className.split(/\s+/)).not.toContain(c)
    }
  })

  it('BT04 — template sanitize même si className métier fourni', () => {
    const { container } = render(
      <ElfisDashboardTemplate
        dashboardId="probe"
        className="fcc up-fcc--unified sales-dashboard"
        header={{ title: 'Tableau de bord' }}
        metrics={<div>m</div>}
        primaryAnalysis={<div>p</div>}
        secondaryAnalysis={<div>s</div>}
        operations={<div>o</div>}
      />,
    )
    const dash = container.querySelector('[data-elfis-dashboard="v1"]')
    expect(dash?.getAttribute('data-blind-template')).toBe('v1')
    for (const c of LAYOUT_ID_CLASSES) {
      expect(dash?.classList.contains(c)).toBe(false)
    }
  })

  it('BT05 — CSS blind force chrome neutre (pas de règles .fcc.up-fcc--unified layout)', () => {
    const css = readFileSync(resolve(__dirname, 'unified-platform.css'), 'utf8')
    expect(css).toMatch(/\[data-blind-template="v1"\]/)
    expect(css).not.toMatch(/\.fcc\.up-fcc--unified\s*\{/)
    expect(css).not.toMatch(/\.sales-dashboard\.up-sales-dash--unified\s*\{/)
    expect(css).not.toMatch(/\.elfis-home\.up-home--unified\s*\{/)
  })

  it('BT06 — doc 35 présente', () => {
    const doc = readFileSync(
      resolve(__dirname, '../../docs/unified-platform/35-blind-template-identity.md'),
      'utf8',
    )
    expect(doc).toMatch(/Blind template identity/)
    expect(doc).toMatch(/data-blind-template/)
    expect(doc).toMatch(/indiscernable|indiscernables|FAIL/i)
  })

  it('BT07 — Home source n’applique plus className layout unifié', () => {
    const src = readFileSync(resolve(__dirname, '../home/ElfisHomePage.tsx'), 'utf8')
    expect(src).not.toMatch(/className=.*elfis-home.*up-home--unified/)
    expect(src).toMatch(/up-dash-band--metrics/)
    expect(src).toMatch(/up-dash-band--primary/)
    expect(src).toMatch(/up-dash-band--secondary/)
  })

  it('BT08 — FCC source : header sans fcc-header layout class', () => {
    const src = readFileSync(
      resolve(__dirname, '../comptapilot/financial-command-center/FinancialCommandCenter.tsx'),
      'utf8',
    )
    expect(src).not.toMatch(/className:\s*'fcc-header/)
    expect(src).not.toMatch(/className=\{unified \? 'fcc/)
    expect(src).toMatch(/up-dash-band--primary/)
    expect(src).toMatch(/up-dash-chip/)
  })

  it('BT09 — Sales source : pas de sales-dashboard wrapper', () => {
    const src = readFileSync(resolve(__dirname, '../pages/sales/SalesDashboardPage.tsx'), 'utf8')
    expect(src).not.toMatch(/sales-dashboard/)
    expect(src).not.toMatch(/up-sales-dash/)
    expect(src).toMatch(/up-dash-band--primary/)
    expect(src).toMatch(/up-dash-list/)
  })

  it('BT10 — bandes metrics/primary/secondary présentes Home + Sales', async () => {
    const home = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    expect(home.container.querySelector('.up-dash-band--metrics')).toBeTruthy()
    expect(home.container.querySelector('.up-dash-band--primary')).toBeTruthy()
    expect(home.container.querySelector('.up-dash-band--secondary')).toBeTruthy()
    home.unmount()

    const sales = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText('Tableau de bord')
    expect(sales.container.querySelector('.up-dash-band--metrics')).toBeTruthy()
    expect(sales.container.querySelector('.up-dash-band--primary')).toBeTruthy()
    expect(sales.container.querySelector('.up-dash-band--secondary')).toBeTruthy()
  })
})
