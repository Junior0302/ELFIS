/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  InsightCard,
  InsightInline,
  InsightList,
  InsightBadge,
  InsightToast,
  InsightBanner,
  InsightStack,
  createInsightAction,
  mapComposerIssuesToInsights,
  mapFinancialAlertToInsight,
  mapDayPriorityToInsight,
  mapHealthToInsights,
  resolveInsightTone,
  sortInsightsByPriority,
  severityRank,
  type Insight,
} from './index'

const baseInsight = (over: Partial<Insight> = {}): Insight => ({
  id: 'i1',
  type: 'attention',
  severity: 'high',
  title: 'Retard client',
  summary: 'Une facture dépasse l’échéance.',
  ...over,
})

afterEach(() => cleanup())

describe('Insight Framework — contrat & tokens', () => {
  it('résout les tons Design System par type', () => {
    const tone = resolveInsightTone('critical', 'critical')
    expect(tone.colorVar).toContain('--pilot-danger')
    expect(tone.defaultRole).toBe('alert')
    expect(tone.labelFr).toBe('Critique')
  })

  it('trie par sévérité Critical → Info', () => {
    const sorted = sortInsightsByPriority([
      baseInsight({ id: 'a', severity: 'info' }),
      baseInsight({ id: 'b', severity: 'critical' }),
      baseInsight({ id: 'c', severity: 'medium' }),
    ])
    expect(sorted.map((i) => i.id)).toEqual(['b', 'c', 'a'])
    expect(severityRank('critical')).toBeLessThan(severityRank('info'))
  })

  it('crée des actions standard FR', () => {
    expect(createInsightAction('fix').label).toBe('Corriger')
    expect(createInsightAction('view').label).toBe('Voir')
    expect(createInsightAction('dismiss').label).toBe('Ignorer')
    expect(createInsightAction('retry').label).toBe('Réessayer')
    expect(createInsightAction('open').label).toBe('Ouvrir')
    expect(createInsightAction('understand').label).toBe('Comprendre')
  })
})

describe('Insight Framework — mappers', () => {
  it('mappe une alerte financière sans inventer de confiance', () => {
    const insight = mapFinancialAlertToInsight({
      id: 'a1',
      code: 'OVERDUE',
      severity: 'warning',
      title: 'Impayé',
      message: 'Facture en retard',
      action: 'Voir',
      source: 'financial',
      value: 120,
      created_at: '2026-08-02T10:00:00Z',
    })
    expect(insight).not.toBeNull()
    expect(insight!.type).toBe('attention')
    expect(insight!.severity).toBe('high')
    expect(insight!.confidence).toBeUndefined()
    expect(insight!.source?.id).toBe('financial')
    expect(insight!.actions?.[0]?.label).toBe('Voir')
  })

  it('retourne null si alerte invalide', () => {
    expect(
      mapFinancialAlertToInsight({
        id: '',
        code: '',
        severity: 'info',
        title: '',
        message: '',
        action: '',
        source: '',
        value: null,
        created_at: '',
      }),
    ).toBeNull()
  })

  it('mappe priorité du jour', () => {
    const insight = mapDayPriorityToInsight({
      id: 'kpi:x',
      level: 'critical',
      title: 'Urgent',
      reason: 'Raison réelle',
      actionLabel: 'Ouvrir',
      href: '/facturation',
      source: 'kpi',
    })
    expect(insight!.severity).toBe('critical')
    expect(insight!.actions?.[0]?.href).toBe('/facturation')
  })

  it('mappe health + recommendations sans inventer', () => {
    const insights = mapHealthToInsights(
      {
        score: 70,
        grade: 'B',
        state: 'active',
        components: [],
        message: 'Message moteur',
      },
      ['Conseil A', ''],
    )
    expect(insights).toHaveLength(2)
    expect(insights[0].summary).toBe('Message moteur')
    expect(insights[1].type).toBe('suggestion')
    expect(insights.every((i) => i.confidence === undefined)).toBe(true)
  })

  it('mappe validation Composer', () => {
    const insights = mapComposerIssuesToInsights([
      { id: 'e1', severity: 'error', message: 'Client requis', field: 'customer' },
      { id: 's1', severity: 'suggestion', message: 'Ajouter une note' },
    ])
    expect(insights[0].type).toBe('critical')
    expect(insights[0].severity).toBe('critical')
    expect(insights[1].type).toBe('suggestion')
    expect(insights[0].context?.field).toBe('customer')
  })
})

describe('Insight Framework — composants', () => {
  it('InsightCard affiche titre + summary, pas de confiance absente', () => {
    render(<InsightCard insight={baseInsight()} />)
    expect(screen.getByText('Retard client')).toBeInTheDocument()
    expect(screen.getByText(/facture dépasse/i)).toBeInTheDocument()
    expect(screen.queryByText(/Confiance/i)).not.toBeInTheDocument()
  })

  it('affiche confiance et source uniquement si fournies', () => {
    render(
      <InsightCard
        insight={baseInsight({
          confidence: 'high',
          source: { id: 'financial', label: 'financial' },
        })}
      />,
    )
    expect(screen.getByText(/Confiance : Élevée/)).toBeInTheDocument()
    expect(screen.getByText('financial')).toBeInTheDocument()
  })

  it('zone Pourquoi ? repliable', async () => {
    const user = userEvent.setup()
    render(
      <InsightCard
        insight={baseInsight({
          details: 'Détail moteur vérifié',
          expandable: true,
        })}
      />,
    )
    expect(screen.queryByText('Détail moteur vérifié')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Pourquoi/i }))
    expect(screen.getByText('Détail moteur vérifié')).toBeInTheDocument()
  })

  it('InsightInline / Banner / Toast / Badge / Stack / List', () => {
    const list = [
      baseInsight({ id: '1' }),
      baseInsight({ id: '2', type: 'success', severity: 'info', title: 'OK' }),
    ]
    const { rerender } = render(<InsightInline insight={list[0]} />)
    expect(screen.getByText('Retard client')).toBeInTheDocument()

    rerender(<InsightBanner insight={list[0]} />)
    expect(document.querySelector('.elf-insight--banner')).toBeTruthy()

    rerender(<InsightToast insight={list[0]} />)
    expect(document.querySelector('.elf-insight--toast')).toBeTruthy()

    rerender(<InsightBadge insight={list[0]} />)
    expect(screen.getByText('Attention')).toBeInTheDocument()

    rerender(<InsightStack insights={list} />)
    expect(document.querySelectorAll('.elf-insight--card').length).toBeGreaterThan(0)

    rerender(<InsightList insights={[]} emptyMessage="Vide" />)
    expect(screen.getByText('Vide')).toBeInTheDocument()

    rerender(<InsightList insights={list} variant="inline" />)
    expect(screen.getByLabelText('Insights')).toBeInTheDocument()
  })

  it('role alert pour critique', () => {
    render(
      <InsightCard insight={baseInsight({ type: 'critical', severity: 'critical' })} />,
    )
    expect(document.querySelector('[role="alert"]')).toBeTruthy()
  })
})
