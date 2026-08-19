import { createElement, type ComponentProps } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import DecisionCard from './components/DecisionCard'
import DecisionList from './components/DecisionList'
import { decisionSeverityLabel, type DecisionItem } from './decisionCenter'

function sampleDecision(over: Partial<DecisionItem> = {}): DecisionItem {
  return {
    id: 'dec-1',
    organization_id: 1,
    decision_type: 'accounting_proposal_requires_review',
    source_type: 'accounting_proposal',
    source_id: 'prop-1',
    status: 'open',
    severity: 'high',
    title: 'Cette proposition comptable nécessite une vérification',
    summary: 'Une revue humaine est recommandée.',
    explanation: 'Écart TTC détecté.',
    recommended_action_type: 'review',
    recommended_action_path: '/accounting/proposals/prop-1',
    required_permission: 'ai.analysis',
    created_by_rule: 'accounting_proposal_requires_review',
    rule_version: '1',
    created_at: '2026-07-30T10:00:00Z',
    updated_at: '2026-07-30T10:00:00Z',
    available_actions: [
      {
        type: 'review',
        label: 'Examiner',
        path: '/accounting/proposals/prop-1',
        enabled: true,
      },
      { type: 'dismiss', label: 'Ignorer', enabled: true },
    ],
    ...over,
  }
}

describe('decisionCenter helpers', () => {
  it('libellés severity hors couleur seule', () => {
    expect(decisionSeverityLabel('high')).toBe('Élevée')
    expect(decisionSeverityLabel('critical')).toBe('Critique')
  })
})

describe('DecisionCard / DecisionList', () => {
  it('rend titre, explication, action et dismiss', () => {
    const onDismiss = vi.fn()
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionCard, {
          decision: sampleDecision(),
          onDismiss,
        }),
      ),
    )
    expect(html).toMatch(/nécessite une vérification/)
    expect(html).toMatch(/Écart TTC/)
    expect(html).toMatch(/href="\/accounting\/proposals\/prop-1"/)
    expect(html).toMatch(/href="\/decisions\/dec-1"/)
    expect(html).toMatch(/Ignorer/)
    expect(html).toMatch(/Élevée/)
  })

  it('masque le bouton non autorisé (pas de path)', () => {
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionCard, {
          decision: sampleDecision({
            available_actions: [{ type: 'review', label: 'Examiner', path: null, enabled: false }],
          }),
        }),
      ),
    )
    expect(html).not.toMatch(/href="\/accounting/)
  })

  it('empty / loading / error', () => {
    const empty = renderToStaticMarkup(
      createElement(MemoryRouter, null, createElement(DecisionList, { items: [] })),
    )
    expect(empty).toMatch(/Aucune décision/)

    const loading = renderToStaticMarkup(
      createElement(MemoryRouter, null, createElement(DecisionList, { items: [], loading: true })),
    )
    expect(loading).toMatch(/aria-busy="true"/)

    const err = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionList, {
          items: [],
          error: 'Erreur réseau',
          onRetry: () => undefined,
        }),
      ),
    )
    expect(err).toMatch(/Erreur réseau/)
    expect(err).toMatch(/Réessayer/)
  })

  it('liste les décisions', () => {
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionList, { items: [sampleDecision()] } as ComponentProps<typeof DecisionList>),
      ),
    )
    expect(html).toMatch(/decision-list/)
    expect(html).toMatch(/nécessite une vérification/)
  })
})
