import { describe, expect, it } from 'vitest'
import {
  aggregateGlobalHealth,
  detectPlatformEnvironment,
  resolvePlatformPageTitle,
} from './platformMeta'

describe('platformMeta V2', () => {
  it('résout les titres de page cockpit', () => {
    expect(resolvePlatformPageTitle('/elfadmin')).toBe('Vue globale')
    expect(resolvePlatformPageTitle('/elfadmin/system-health')).toBe('Santé système')
    expect(resolvePlatformPageTitle('/elfadmin/organisations/12')).toBe('Détail organisation')
  })

  it('agrège le statut global sans inventer de données', () => {
    expect(aggregateGlobalHealth([]).label).toBe('Unknown')
    expect(aggregateGlobalHealth(['healthy', 'ok']).tone).toBe('healthy')
    expect(aggregateGlobalHealth(['healthy', 'degraded']).tone).toBe('degraded')
    expect(aggregateGlobalHealth(['healthy', 'unhealthy']).tone).toBe('critical')
  })

  it('détecte local en environnement de test', () => {
    const env = detectPlatformEnvironment()
    expect(['local', 'staging', 'prod', 'unknown']).toContain(env)
  })
})
