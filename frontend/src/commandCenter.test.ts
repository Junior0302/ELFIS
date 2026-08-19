import { createElement, type ComponentProps } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import CommandCenter from './components/CommandCenter'
import {
  formatCommandMetric,
  healthStatusLabel,
  severityLabel,
  type CommandCenterData,
} from './commandCenter'

function sample(over: Partial<CommandCenterData> = {}): CommandCenterData {
  return {
    organization_name: 'CreaLab Auto',
    priorities: [
      {
        id: 'invoices-overdue',
        severity: 'high',
        title: '2 facture(s) en retard',
        description: '500.00 € à relancer.',
        action_path: '/facturation',
        permission: 'invoice.read',
      },
    ],
    smart_summary: {
      headline: 'Voici l’état actuel de votre activité.',
      has_financial_data: true,
      metrics: [
        { key: 'customers', label: 'Clients', value: 3, path: '/clients' },
        { key: 'unpaid_amount', label: 'Montant dû', value: 1200, unit: 'EUR', path: '/facturation' },
      ],
    },
    activity_timeline: [
      {
        id: 'invoice-1',
        type: 'invoice_created',
        title: 'Facture créée',
        description: 'FAC-001',
        occurred_at: '2026-07-30T10:00:00Z',
        path: '/facturation',
      },
    ],
    ai_insights: {
      status: 'empty',
      title: 'À examiner',
      message: 'Aucune décision ne nécessite votre attention actuellement.',
      insights: [],
      work_queue_path: '/work-queue',
      counts: { todo: 0, in_progress: 0, waiting: 0, completed: 0 },
    },
    quick_actions: [
      {
        key: 'new_customer',
        label: 'Nouveau client',
        description: 'Créer une fiche client',
        path: '/clients',
        enabled: true,
      },
    ],
    system_health: {
      services: [
        { key: 'billing', label: 'Facturation / abonnement', status: 'ok', detail: 'Abonnement actif.' },
        { key: 'vault', label: 'Vault', status: 'ok', detail: 'Espace documentaire accessible.' },
      ],
    },
    generated_at: '2026-07-30T10:00:00Z',
    ...over,
  }
}

function renderCC(props: Partial<ComponentProps<typeof CommandCenter>> = {}) {
  return renderToStaticMarkup(
    createElement(
      MemoryRouter,
      null,
      createElement(CommandCenter, {
        data: sample(),
        loading: false,
        error: '',
        onRetry: () => undefined,
        ...props,
      }),
    ),
  )
}

describe('commandCenter helpers', () => {
  it('formate les métriques et sévérités', () => {
    expect(formatCommandMetric({ key: 'x', label: 'x', value: 3 })).toBe('3')
    expect(formatCommandMetric({ key: 'x', label: 'x', value: 1200, unit: 'EUR' })).toMatch(/€/)
    expect(severityLabel('critical')).toBe('Critique')
    expect(healthStatusLabel('degraded')).toBe('Dégradé')
  })
})

describe('CommandCenter', () => {
  it('affiche loading accessible', () => {
    const html = renderCC({ data: null, loading: true })
    expect(html).toMatch(/aria-busy="true"/)
  })

  it('affiche erreur avec réessayer', () => {
    const html = renderCC({ data: null, loading: false, error: 'Service indisponible' })
    expect(html).toMatch(/Service indisponible/)
    expect(html).toMatch(/Réessayer/)
  })

  it('rend priorités, résumé, timeline, IA, santé et actions', () => {
    const html = renderCC()
    expect(html).toMatch(/Que dois-je faire maintenant/)
    expect(html).toMatch(/2 facture\(s\) en retard/)
    expect(html).toMatch(/Clients/)
    expect(html).toMatch(/Facture créée/)
    expect(html).toMatch(/Aucune décision ne nécessite votre attention/)
    expect(html).toMatch(/À examiner/)
    expect(html).toMatch(/Boîte de travail/)
    expect(html).toMatch(/href="\/work-queue"/)
    expect(html).toMatch(/Vault/)
    expect(html).toMatch(/Nouveau client/)
    expect(html).toMatch(/command-center-grid/)
  })

  it('affiche jusqu’à 3 insights Decision Center', () => {
    const html = renderCC({
      data: sample({
        ai_insights: {
          status: 'ready',
          title: 'À examiner',
          message: '',
          insights: [
            {
              decision_id: 'd1',
              title: 'Proposition à vérifier',
              summary: 'Écart détecté',
              severity: 'high',
              action_label: 'Examiner',
              action_path: '/decisions/d1',
            },
          ],
        },
      }),
    })
    expect(html).toMatch(/Proposition à vérifier/)
    expect(html).toMatch(/href="\/decisions\/d1"/)
    expect(html).toMatch(/Élevée/)
    expect(html).toMatch(/href="\/work-queue"/)
  })

  it('empty priorities propre', () => {
    const html = renderCC({
      data: sample({ priorities: [] }),
    })
    expect(html).toMatch(/Rien d’urgent/)
  })

  it('n’affiche pas Search/DI inventés', () => {
    const html = renderCC()
    expect(html).not.toMatch(/Document Intelligence/)
    expect(html).not.toMatch(/>Search</)
  })
})
