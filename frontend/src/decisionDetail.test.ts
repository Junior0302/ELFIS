import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import DecisionActionPanel from './components/DecisionActionPanel'
import DecisionEvidenceList from './components/DecisionEvidenceList'
import DecisionExecutionStatusBadge from './components/DecisionExecutionStatus'
import DecisionHistory from './components/DecisionHistory'
import DecisionResolutionPanel from './components/DecisionResolutionPanel'
import {
  decisionStatusLabel,
  executionStatusLabel,
  type DecisionDetail,
  type DecisionItem,
} from './decisionCenter'

function sampleDetail(over: Partial<DecisionDetail> = {}): DecisionDetail {
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
    execution_status: 'idle',
    available_actions: [
      {
        action_type: 'open_accounting_proposal',
        type: 'open_accounting_proposal',
        label: 'Examiner la proposition',
        method: 'NAVIGATE',
        action_path: '/accounting/proposals/prop-1',
        path: '/accounting/proposals/prop-1',
        enabled: true,
      },
      {
        action_type: 'validate_accounting_proposal',
        type: 'validate_accounting_proposal',
        label: 'Valider la proposition',
        method: 'POST',
        requires_confirmation: true,
        enabled: true,
      },
      {
        action_type: 'dismiss',
        type: 'dismiss',
        label: 'Ignorer',
        method: 'POST',
        enabled: true,
      },
    ],
    evidence: [
      {
        type: 'financial_difference',
        label: 'Écart détecté',
        value: '12,50 €',
        description: 'Le total des lignes ne correspond pas au montant TTC.',
      },
    ],
    history: [
      {
        id: 'h1',
        kind: 'created',
        label: 'Décision créée',
        at: '2026-07-30T10:00:00Z',
      },
    ],
    what_was_detected: 'Écart détecté',
    why_it_matters: 'Important',
    what_to_do: 'Examiner',
    what_happens_after: 'Résolution auto',
    ...over,
  }
}

describe('decision execution helpers', () => {
  it('libellés statut / exécution', () => {
    expect(decisionStatusLabel('resolved')).toBe('Résolue')
    expect(executionStatusLabel('failed')).toBe('Échouée')
  })
})

describe('Decision detail components', () => {
  it('affiche evidence et historique', () => {
    const evidence = renderToStaticMarkup(
      createElement(DecisionEvidenceList, { evidence: sampleDetail().evidence }),
    )
    expect(evidence).toMatch(/Écart détecté/)
    expect(evidence).toMatch(/12,50/)

    const history = renderToStaticMarkup(
      createElement(DecisionHistory, { items: sampleDetail().history }),
    )
    expect(history).toMatch(/Décision créée/)
  })

  it('affiche actions principales et secondaires', () => {
    const onExecute = vi.fn()
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionActionPanel, {
          decision: sampleDetail() as DecisionItem,
          onExecute,
          onDismiss: () => undefined,
        }),
      ),
    )
    expect(html).toMatch(/Examiner la proposition/)
    expect(html).toMatch(/Valider la proposition/)
    expect(html).toMatch(/Ignorer/)
    expect(html).toMatch(/href="\/accounting\/proposals\/prop-1"/)
  })

  it('affiche raison de désactivation', () => {
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionActionPanel, {
          decision: sampleDetail({
            available_actions: [
              {
                type: 'validate_accounting_proposal',
                label: 'Valider',
                enabled: false,
                disabled_reason: 'Permission insuffisante pour valider.',
              },
            ],
          }),
          onExecute: () => undefined,
        }),
      ),
    )
    expect(html).toMatch(/Permission insuffisante/)
    expect(html).toMatch(/disabled/)
  })

  it('affiche état d’exécution et panneau résolu', () => {
    const exec = renderToStaticMarkup(
      createElement(DecisionExecutionStatusBadge, {
        status: 'failed',
        errorMessage: 'Confirmations requises',
      }),
    )
    expect(exec).toMatch(/Échouée/)
    expect(exec).toMatch(/Confirmations requises/)

    const resolved = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DecisionResolutionPanel, {
          resolvedAt: '2026-07-30T12:00:00Z',
          lastAction: 'validate_accounting_proposal',
          sourcePath: '/accounting/proposals/prop-1',
        }),
      ),
    )
    expect(resolved).toMatch(/Décision résolue/)
    expect(resolved).toMatch(/Command Center/)
  })
})
