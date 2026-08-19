/**
 * @vitest-environment node
 */
import { describe, expect, it } from 'vitest'
import { mapHomeSignalsToInsights } from './homeInsights'

describe('homeInsights', () => {
  it('mappe unread → insight attention sans inventer de KPI', () => {
    const insights = mapHomeSignalsToInsights([
      {
        id: 'notifs',
        label: '2 notifications non lues',
        tone: 'attention',
        href: '/notifications',
      },
    ])
    expect(insights[0]?.type).toBe('attention')
    expect(insights[0]?.title).toMatch(/2 notifications/)
    expect(insights[0]?.source?.id).toBe('home-cockpit')
    expect(JSON.stringify(insights)).not.toMatch(/facture|prospect/i)
  })

  it('empty → confirmation calme honnête', () => {
    const insights = mapHomeSignalsToInsights([])
    expect(insights).toHaveLength(1)
    expect(insights[0]?.type).toBe('confirmation')
    expect(insights[0]?.title).toMatch(/calme/i)
  })
})
