import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import WorkQueueItemCard from './components/WorkQueueItemCard'
import { bucketLabel, emptyCopy, type WorkQueueItem } from './workQueue'

function sampleItem(over: Partial<WorkQueueItem> = {}): WorkQueueItem {
  return {
    decision_id: 'd1',
    decision_type: 'accounting_proposal_requires_review',
    bucket: 'todo',
    status: 'open',
    execution_status: 'idle',
    severity: 'high',
    title: 'Proposition à vérifier',
    summary: 'Écart détecté',
    source_type: 'accounting_proposal',
    source_id: 'p1',
    created_at: '2026-07-30T10:00:00Z',
    updated_at: '2026-07-30T10:00:00Z',
    is_blocking: true,
    progress_label: 'À traiter',
    available_actions: [
      { type: 'start', label: 'Commencer', method: 'POST', enabled: true },
      {
        type: 'open_detail',
        label: 'Ouvrir',
        method: 'NAVIGATE',
        path: '/decisions/d1',
        enabled: true,
      },
      { type: 'dismiss', label: 'Ignorer', method: 'POST', enabled: true },
    ],
    ...over,
  }
}

describe('workQueue helpers', () => {
  it('libellés buckets et empty states', () => {
    expect(bucketLabel('todo')).toBe('À traiter')
    expect(emptyCopy('waiting', false).title).toMatch(/attente/i)
    expect(emptyCopy('todo', true).description).toMatch(/filtres/)
  })
})

describe('WorkQueueItemCard', () => {
  it('affiche severity, commencer et détail', () => {
    const onStart = vi.fn()
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(WorkQueueItemCard, { item: sampleItem(), onStart }),
      ),
    )
    expect(html).toMatch(/Proposition à vérifier/)
    expect(html).toMatch(/Commencer/)
    expect(html).toMatch(/href="\/decisions\/d1"/)
    expect(html).toMatch(/Élevée|Bloquant/)
  })

  it('affiche waiting reason', () => {
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(WorkQueueItemCard, {
          item: sampleItem({
            bucket: 'waiting',
            waiting_reason: {
              code: 'analysis_in_progress',
              label: 'Analyse documentaire en cours',
              description: 'Traitement système en cours.',
            },
            available_actions: [
              { type: 'open_detail', label: 'Ouvrir', path: '/decisions/d1', enabled: true },
            ],
          }),
        }),
      ),
    )
    expect(html).toMatch(/Analyse documentaire en cours/)
  })
})
