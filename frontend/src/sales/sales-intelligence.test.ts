/** Sales Intelligence helpers — S1.7 */
import { describe, expect, it } from 'vitest'
import { SALES_NAV_ITEMS } from './salesNavModel'
import {
  focusToneLabel,
  intelligencePath,
  severityTone,
} from './salesIntelligence'

describe('Sales Intelligence V1', () => {
  it('expose la navigation Priorités', () => {
    expect(SALES_NAV_ITEMS.some((i) => i.to === '/sales/intelligence')).toBe(true)
  })

  it('construit les chemins intelligence', () => {
    expect(intelligencePath()).toBe('/sales/intelligence')
    expect(intelligencePath(9)).toBe('/sales/intelligence/9')
  })

  it('mappe severity et focus tones', () => {
    expect(severityTone('critical')).toBe('danger')
    expect(severityTone('high')).toBe('warn')
    expect(focusToneLabel('no_urgent_focus')).toBe('Aucune urgence')
    expect(focusToneLabel('urgent')).toBe('Urgent')
  })
})
