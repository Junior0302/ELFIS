/**
 * Alignement structurel Home / FCC / Sales — même ElfisPageFrame + ElfisDashboardTemplate.
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ElfisHomePage from '../home/ElfisHomePage'
import SalesDashboardPage from '../pages/sales/SalesDashboardPage'

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

describe('Page frame layout control — 3 dashboards', () => {
  beforeEach(() => {
    cleanup()
  })
  afterEach(() => {
    cleanup()
  })

  it('Home rend ElfisPageFrame + ElfisDashboardTemplate (sections 8/4)', () => {
    const { container } = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const frame = container.querySelector('[data-elfis-page-frame="v1"]')
    const dash = container.querySelector('[data-elfis-dashboard="v1"]')
    expect(frame).toBeTruthy()
    expect(dash).toBeTruthy()
    expect(frame?.contains(dash)).toBe(true)
    expect(dash?.getAttribute('data-dashboard-id')).toBe('home')
    expect(container.querySelector('[data-dashboard-slot="primary"]')).toBeTruthy()
    expect(frame?.classList.contains('up-page-frame--pad-comfortable')).toBe(true)
  })

  it('Sales Dashboard rend le même frame + template', async () => {
    const { container } = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText(/Tableau de bord/i)
    const frame = container.querySelector('[data-elfis-page-frame="v1"]')
    const dash = container.querySelector('[data-elfis-dashboard="v1"]')
    expect(frame).toBeTruthy()
    expect(dash?.getAttribute('data-dashboard-id')).toBe('sales')
    expect(frame?.contains(dash)).toBe(true)
    expect(frame?.classList.contains('up-page-frame--pad-comfortable')).toBe(true)
  })

  it('Home et Sales partagent classes frame / padding', async () => {
    const home = render(
      <MemoryRouter>
        <ElfisHomePage />
      </MemoryRouter>,
    )
    const homeFrame = home.container.querySelector('[data-elfis-page-frame="v1"]')
    const homePad = homeFrame?.getAttribute('data-page-frame-padding')
    home.unmount()

    const sales = render(
      <MemoryRouter>
        <SalesDashboardPage />
      </MemoryRouter>,
    )
    await screen.findByText(/Tableau de bord/i)
    const salesFrame = sales.container.querySelector('[data-elfis-page-frame="v1"]')
    expect(salesFrame?.getAttribute('data-page-frame-padding')).toBe(homePad)
    expect(homePad).toBe('comfortable')
  })

  it('CSS : max-width 1680 + blind template', () => {
    const upCss = readFileSync(resolve(__dirname, 'unified-platform.css'), 'utf8')
    expect(upCss).toMatch(/--up-page-max-width:\s*1680px/)
    expect(upCss).toMatch(/\[data-blind-template="v1"\]/)
  })
})
