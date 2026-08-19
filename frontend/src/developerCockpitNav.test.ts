import { describe, expect, it } from 'vitest'
import { canAccessDeveloperCockpit, developerCockpitSections } from './developerCockpitNav'

describe('Developer Cockpit navigation', () => {
  it('expose les sections mission', () => {
    const labels = developerCockpitSections.flatMap((s) => s.items.map((i) => i.label))
    for (const label of [
      'Vue technique',
      'Services',
      'API',
      'Workers',
      'Jobs & Queues',
      'Event Bus',
      'Logs',
      'Traces',
      'Base de données',
      'Feature Flags',
      'Diagnostics',
      'Audit technique',
    ]) {
      expect(labels).toContain(label)
    }
  })

  it('autorise platform.admin flag', () => {
    expect(canAccessDeveloperCockpit({ isPlatformAdmin: true })).toBe(true)
  })

  it('autorise permissions techniques explicites', () => {
    expect(canAccessDeveloperCockpit({ permissions: ['platform.developer'] })).toBe(true)
    expect(canAccessDeveloperCockpit({ permissions: ['platform.sre'] })).toBe(true)
    expect(canAccessDeveloperCockpit({ permissions: ['platform.support'] })).toBe(false)
  })
})
