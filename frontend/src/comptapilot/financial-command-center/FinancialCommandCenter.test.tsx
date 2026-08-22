/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { FinancialOverview } from '../../services/financialApi'

const overviewMock = vi.fn()
const getLaunchDashboardMock = vi.fn()

vi.mock('../../auth', () => ({
  useAuth: () => ({
    token: 'tok',
    orgId: 7,
    user: { id: 1, is_platform_admin: false, first_name: 'Chris' },
    memberships: [
      {
        membership_id: 1,
        organization_id: 7,
        organization_name: 'Crealab Auto',
        role: 'owner',
        permissions: [],
        plan: 'pro',
        country: 'FR',
      },
    ],
  }),
}))

vi.mock('../../subscriptionContext', () => ({
  useSubscription: () => ({
    subscription: {
      plan: 'pro',
      status: 'active',
      access_granted: true,
      price_eur: 19,
      configured: true,
      trial_end: null,
      current_period_end: null,
      cancel_at_period_end: false,
    },
    loading: false,
  }),
}))

vi.mock('../../subscription', async () => {
  const actual = await vi.importActual<typeof import('../../subscription')>('../../subscription')
  return {
    ...actual,
    hasFinancialEntitlement: () => true,
  }
})

vi.mock('../../services/financialApi', async () => {
  const actual = await vi.importActual<typeof import('../../services/financialApi')>(
    '../../services/financialApi',
  )
  return {
    ...actual,
    financialApi: {
      ...actual.financialApi,
      overview: (...args: unknown[]) => overviewMock(...args),
    },
  }
})

vi.mock('../../api', () => ({
  api: {
    getLaunchDashboard: (...args: unknown[]) => getLaunchDashboardMock(...args),
  },
}))

import FinancialCommandCenter from './FinancialCommandCenter'
import DashboardPage from '../../pages/DashboardPage'

/** Titre unifié du cockpit financier (ElfisDashboardTemplate). */
const FCC_PAGE_TITLE = /tableau de bord/i

function sampleOverview(over: Partial<FinancialOverview> = {}): FinancialOverview {
  return {
    computed_at: '2026-08-02T12:00:00Z',
    has_data: true,
    kpis: [
      {
        id: 'tresorerie',
        label: 'Trésorerie',
        value: 15000,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'up', delta: 500, delta_pct: 3.4, previous: 14500 },
        hint: 'Solde agrégé',
      },
      {
        id: 'tva',
        label: 'TVA estimée',
        value: 1200,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'flat', delta: 0, delta_pct: 0, previous: 1200 },
        hint: 'Estimation',
      },
    ],
    alerts: [],
    health: {
      score: 77,
      grade: 'B',
      state: 'active',
      components: [{ id: 'cash', label: 'Cash', score: 20, max_score: 25, detail: 'ok' }],
      message: null,
    },
    charts: {
      revenue_vs_expenses: [
        { period: '2026-06', revenue: 1000, expenses: 400 },
        { period: '2026-07', revenue: 1200, expenses: 500 },
      ],
      treasury: [
        { period: '2026-06', value: 8000 },
        { period: '2026-07', value: 9000 },
      ],
      expense_breakdown: [],
      categories: [],
      ca_evolution: [
        { period: '2026-06', value: 1000 },
        { period: '2026-07', value: 1200 },
      ],
    },
    trends: {
      monthly: {
        points: [],
        comparison: {
          revenue: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          expenses: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          result: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        },
      },
      weekly: {
        points: [],
        comparison: {
          revenue: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          expenses: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          result: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        },
      },
      yearly: {
        points: [],
        comparison: {
          revenue: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          expenses: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          result: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        },
      },
    },
    sync: {
      connections: 1,
      errors: 0,
      last_sync_at: '2026-08-02T11:00:00Z',
      age_hours: 1,
      failed_runs_7d: 0,
      ok_runs_7d: 3,
      status: 'fresh',
    },
    documents_to_process: 2,
    recent_activity: [],
    recommendations: ['Surveiller la trésorerie'],
    ...over,
  }
}

function renderFcc(path = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/dashboard" element={<FinancialCommandCenter />} />
        <Route path="/finance" element={<div>Finance page</div>} />
        <Route path="/banque" element={<div>Banque page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function sectionOrder(): string[] {
  return Array.from(document.querySelectorAll('[data-fcc-section]')).map(
    (el) => el.getAttribute('data-fcc-section') || '',
  )
}

describe('FinancialCommandCenter S1.2.6 Premium V2', () => {
  beforeEach(() => {
    overviewMock.mockReset()
    getLaunchDashboardMock.mockReset()
    overviewMock.mockResolvedValue(sampleOverview())
    getLaunchDashboardMock.mockResolvedValue({
      workspace_ready: true,
      user: { display_name: 'Chris' },
      organization: { name: 'Demo' },
      onboarding: {
        completed_steps: 5,
        total_steps: 5,
        progress: 100,
        steps: [],
        recommended_action: null,
        all_completed: true,
      },
      quick_actions: [],
      recent_activity: [],
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('DashboardPage exporte le FCC (route /dashboard)', () => {
    expect(DashboardPage).toBe(FinancialCommandCenter)
  })

  it('affiche le FCC sans onboarding ELFIS / LaunchDashboard', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: FCC_PAGE_TITLE })).toBeInTheDocument()
    })
    expect(document.querySelector('[data-fcc="v1"]')).toBeTruthy()
    expect(document.querySelector('[data-fcc-layout="s126"]')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/parcours de démarrage/i)
    expect(document.body.textContent).not.toMatch(/LaunchDashboard/i)
    expect(screen.queryByText(/préparez l’espace/i)).not.toBeInTheDocument()
  })

  it('header premium : org, Engine Ready, source, sync', async () => {
    renderFcc()
    await waitFor(() => {
      expect(document.querySelector('[data-fcc-engine="ready"]')).toBeTruthy()
    })
    expect(screen.getByText('Engine Ready')).toBeInTheDocument()
    expect(document.querySelector('[data-fcc-org="true"]')?.textContent).toMatch(/crealab auto/i)
    expect(document.querySelector('[data-fcc-header-meta="true"]')?.textContent).toMatch(
      /financial engine/i,
    )
    expect(screen.getByRole('button', { name: /^exporter$/i })).toBeInTheDocument()
  })

  it('Exporter affiche toast bientôt (pas de fausse export)', async () => {
    const user = userEvent.setup()
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^exporter$/i })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /^exporter$/i }))
    expect(screen.getByText(/export bientôt disponible/i)).toBeInTheDocument()
  })

  it('place Essentiel avant Analyser (KPI avant graphiques primaires)', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^essentiel$/i })).toBeInTheDocument()
    })
    const order = sectionOrder()
    expect(order.indexOf('essentiel')).toBeLessThan(order.indexOf('primary'))
    expect(order.indexOf('primary')).toBeLessThan(order.indexOf('secondary'))
    expect(order.indexOf('secondary')).toBeLessThan(order.indexOf('operations'))
    expect(order.indexOf('operations')).toBeLessThan(order.indexOf('activity'))
  })

  it('layout Analyser : héros full-width + graphiques secondaires', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /revenus vs dépenses/i })).toBeInTheDocument()
    })
    const primary = document.querySelector('[data-fcc-section="primary"]') as HTMLElement
    expect(primary.querySelector('.up-chart-card--hero')).toBeTruthy()
    const secondary = document.querySelector('[data-fcc-section="secondary"]') as HTMLElement
    expect(within(secondary).getByRole('heading', { name: /^trésorerie$/i })).toBeInTheDocument()
    expect(within(secondary).getByRole('heading', { name: /évolution ca/i })).toBeInTheDocument()
    expect(
      document.querySelectorAll('[data-fcc-section="primary"] [data-widget-id^="chart-"], [data-fcc-section="secondary"] [data-widget-id^="chart-"]').length,
    ).toBeGreaterThanOrEqual(3)
  })

  it('marque les graphiques faibles si historique insuffisant (pas de fausse courbe)', async () => {
    overviewMock.mockResolvedValue(
      sampleOverview({
        charts: {
          revenue_vs_expenses: [{ period: '2026-07', revenue: 100, expenses: 50 }],
          treasury: [{ period: '2026-07', value: 100 }],
          ca_evolution: [{ period: '2026-07', value: 100 }],
          expense_breakdown: [],
          categories: [],
        },
      }),
    )
    renderFcc()
    await waitFor(() => {
      expect(document.querySelectorAll('[data-chart-weak="1"]').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('affiche les KPI Engine et le disclaimer health', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getAllByText('Trésorerie').length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getByText(/15[\s\u00a0]?000/)).toBeInTheDocument()
    expect(
      screen.getAllByText(/ne remplace pas un conseil comptable/i).length,
    ).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/conseils moteur/i)).toBeInTheDocument()
    expect(screen.getAllByText(/surveiller la trésorerie/i).length).toBeGreaterThanOrEqual(1)
  })

  it('banques/sync dans Essentiel si signal réel, et toujours dans Traiter', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^traiter$/i })).toBeInTheDocument()
    })
    const essentiel = document.querySelector('[data-fcc-section="essentiel"]') as HTMLElement
    expect(within(essentiel).getByRole('heading', { name: /banques \/ sync/i })).toBeInTheDocument()
    expect(document.querySelector('[data-fcc-sync="true"]')).toBeTruthy()
    expect(screen.getAllByText(/fresh/i).length).toBeGreaterThanOrEqual(1)
  })

  it('banques hors Essentiel si aucun signal sync', async () => {
    overviewMock.mockResolvedValue(
      sampleOverview({
        sync: {
          connections: 0,
          errors: 0,
          last_sync_at: null,
          age_hours: null,
          failed_runs_7d: 0,
          ok_runs_7d: 0,
          status: 'none',
        },
      }),
    )
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^essentiel$/i })).toBeInTheDocument()
    })
    const essentiel = document.querySelector('[data-fcc-section="essentiel"]') as HTMLElement
    expect(within(essentiel).queryByRole('heading', { name: /banques \/ sync/i })).toBeNull()
    expect(document.querySelector('[data-fcc-sync="true"]')).toBeTruthy()
  })

  it('documents à traiter une fois dans Essentiel (pas de doublon KPI docs)', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^essentiel$/i })).toBeInTheDocument()
    })
    const essentiel = document.querySelector('[data-fcc-section="essentiel"]')!
    const docsInEssentiel = within(essentiel as HTMLElement).getAllByRole('heading', {
      name: /documents à traiter/i,
    })
    expect(docsInEssentiel).toHaveLength(1)
  })

  it('widgets Comprendre en 3 colonnes (health, prévisions, flux)', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /financial health score/i })).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: /prévisions de trésorerie/i })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /encaissements & décaissements/i }),
    ).toBeInTheDocument()
    const understand = document.querySelector('.fcc-understand-grid')
    expect(understand?.querySelectorAll('[data-widget-id]').length).toBe(3)
  })

  it('empty prévisions / flux sans inventer de chiffres maquette', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByText(/prévision indisponible/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/flux prévisionnels indisponibles/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /connecter une banque/i })).toHaveAttribute(
      'href',
      '/banque',
    )
    expect(document.body.textContent).not.toMatch(/15[\s\u00a0]?420/)
    expect(document.body.textContent).not.toMatch(/15420/)
  })

  it('timeline activité récente (icône, type, heure, badge)', async () => {
    overviewMock.mockResolvedValue(
      sampleOverview({
        recent_activity: [
          {
            type: 'facture',
            label: 'FAC-2026-0001 - Serge Ibaka',
            amount: 1200,
            date: '2026-08-02T10:00:00Z',
            meta: 'Envoyée',
            created_at: '2026-08-02T10:05:00Z',
          },
        ],
      }),
    )
    renderFcc()
    await waitFor(() => {
      expect(screen.getByText(/FAC-2026-0001/i)).toBeInTheDocument()
    })
    expect(document.querySelector('.fcc-timeline')).toBeTruthy()
    expect(document.querySelector('.fcc-timeline__icon')).toBeTruthy()
    expect(screen.getByText('facture')).toBeInTheDocument()
    expect(screen.getByText(/envoyée/i)).toBeInTheDocument()
  })

  it('écritures / rapprochements N/A honnêtes si absents de overview', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByText(/écritures à valider/i)).toBeInTheDocument()
    })
    expect(screen.getAllByText('N/A').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText(/signal non exposé par overview/i).length).toBeGreaterThanOrEqual(2)
  })

  it('refresh global sans navigation', async () => {
    const user = userEvent.setup()
    renderFcc()
    await waitFor(() => expect(overviewMock).toHaveBeenCalled())
    overviewMock.mockClear()
    await user.click(screen.getByRole('button', { name: /^actualiser$/i }))
    await waitFor(() => {
      expect(overviewMock).toHaveBeenCalledWith('tok', 7, true)
    })
    expect(screen.getByRole('heading', { name: FCC_PAGE_TITLE })).toBeInTheDocument()
  })

  it('refresh widget discret avec aria-label', async () => {
    const user = userEvent.setup()
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /actualiser revenus vs dépenses/i })).toBeInTheDocument()
    })
    overviewMock.mockClear()
    await user.click(screen.getByRole('button', { name: /actualiser revenus vs dépenses/i }))
    await waitFor(() => {
      expect(overviewMock).toHaveBeenCalledWith('tok', 7, true)
    })
  })

  it('lien analyse détaillée vers /finance', async () => {
    renderFcc()
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /analyse détaillée/i })).toHaveAttribute(
        'href',
        '/finance',
      )
    })
  })

  it('a11y basique : sections titrées + widgets chart', async () => {
    renderFcc()
    await waitFor(() => {
      expect(document.querySelector('[data-fcc-section="essentiel"]')).toHaveAttribute(
        'aria-labelledby',
        'fcc-essentials',
      )
    })
    expect(document.querySelector('[data-fcc-section="primary"]')).toBeTruthy()
    expect(document.querySelector('[data-widget-id="chart-rev"]')).toBeTruthy()
  })

  it('empty state activité / has_data false reste honnête', async () => {
    overviewMock.mockResolvedValue(
      sampleOverview({
        has_data: false,
        kpis: [],
        recent_activity: [],
        charts: {
          revenue_vs_expenses: [],
          treasury: [],
          ca_evolution: [],
          expense_breakdown: [],
          categories: [],
        },
        health: { score: null, grade: null, state: 'setup', components: [], message: 'Setup' },
        sync: {
          connections: 0,
          errors: 0,
          last_sync_at: null,
          age_hours: null,
          failed_runs_7d: 0,
          ok_runs_7d: 0,
          status: 'none',
        },
      }),
    )
    renderFcc()
    await waitFor(() => {
      expect(screen.getByText(/prévision indisponible/i)).toBeInTheDocument()
    })
    expect(screen.queryByText(/parcours de démarrage/i)).not.toBeInTheDocument()
  })

  it('bandeau org incomplete si workspace non prêt', async () => {
    getLaunchDashboardMock.mockResolvedValue({
      workspace_ready: false,
      user: { display_name: null },
      organization: { name: 'Demo' },
      onboarding: {
        completed_steps: 0,
        total_steps: 5,
        progress: 0,
        steps: [],
        recommended_action: null,
        all_completed: false,
      },
      quick_actions: [],
      recent_activity: [],
    })
    renderFcc()
    await waitFor(() => {
      expect(screen.getByText(/informations nécessaires/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: /compléter dans elfis/i })).toHaveAttribute(
      'href',
      '/platform/organization',
    )
  })
})
