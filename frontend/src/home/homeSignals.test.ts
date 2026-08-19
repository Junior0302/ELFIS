/**
 * @vitest-environment node
 */
import { describe, expect, it } from 'vitest'
import {
  buildDetectionSignals,
  buildDayDomainCards,
  buildHealthLamps,
} from './homeSignals'

describe('homeSignals honesty', () => {
  it('n’émet un signal notifs que si unread > 0', () => {
    const none = buildDetectionSignals({
      connected: true,
      orgName: 'Acme',
      orgOk: true,
      unreadNotifications: 0,
      syncOk: true,
      lastProductId: 'comptapilot',
    })
    expect(none.find((s) => s.id === 'notifs')).toBeUndefined()

    const some = buildDetectionSignals({
      connected: true,
      orgName: 'Acme',
      orgOk: true,
      unreadNotifications: 2,
      syncOk: true,
      lastProductId: 'comptapilot',
    })
    expect(some.find((s) => s.id === 'notifs')?.label).toMatch(/2 notifications/)
  })

  it('cartes journée sans KPI inventés', () => {
    const cards = buildDayDomainCards({
      orgName: 'Acme',
      orgRole: 'owner',
      lastProductId: null,
      lastProductAt: null,
      unreadNotifications: 0,
    })
    expect(cards.find((c) => c.id === 'finance')?.summary).toMatch(/aucun signal/i)
    expect(cards.find((c) => c.id === 'documents')?.status).toBe('Non agrégé')
    expect(JSON.stringify(cards)).not.toMatch(/facture|prospect/i)
  })

  it('health n’invente pas stockage/IA/emails', () => {
    const lamps = buildHealthLamps({
      connected: true,
      orgOk: true,
      syncOk: true,
      syncMode: 'polling',
      unreadKnown: true,
    })
    const ids = lamps.map((l) => l.id)
    expect(ids).toEqual(['connection', 'org', 'sync', 'notifications'])
    expect(ids).not.toContain('storage')
    expect(ids).not.toContain('ai')
    expect(ids).not.toContain('email')
  })
})
