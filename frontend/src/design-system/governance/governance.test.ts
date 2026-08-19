/**
 * Governance registry integrity + Design System 1.0 certification (E1.6–E1.7).
 */
import { describe, expect, it } from 'vitest'
import {
  BUILD,
  DATE,
  DESIGN_SYSTEM_CERTIFICATION,
  DESIGN_SYSTEM_NAME,
  DESIGN_SYSTEM_VERSION,
  MATURITY,
  VERSION,
  certificationReadyCount,
  COMPONENT_MATURITY_REGISTRY,
  DESIGN_SCORE_CATEGORIES,
  globalDesignScore,
  healthScore,
  PILOT_READINESS,
} from '../index'

describe('E1.6 Design Governance', () => {
  it('registre de maturité couvre les composants publics attendus', () => {
    const ids = COMPONENT_MATURITY_REGISTRY.map((c) => c.id)
    expect(ids).toContain('button')
    expect(ids).toContain('dialog')
    expect(ids).toContain('app-launcher')
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('healthScore est borné 0–100 et basé sur critères', () => {
    for (const c of COMPONENT_MATURITY_REGISTRY) {
      const s = healthScore(c)
      expect(s).toBeGreaterThanOrEqual(0)
      expect(s).toBeLessThanOrEqual(100)
    }
  })

  it('design scores ont une rationale et un global cohérent', () => {
    expect(DESIGN_SCORE_CATEGORIES).toHaveLength(11)
    for (const c of DESIGN_SCORE_CATEGORIES) {
      expect(c.score).toBeGreaterThanOrEqual(0)
      expect(c.score).toBeLessThanOrEqual(100)
      expect(c.rationale.length).toBeGreaterThan(10)
    }
    const g = globalDesignScore()
    expect(g).toBeGreaterThan(50)
    expect(g).toBeLessThan(90)
  })

  it('pilot readiness couvre la suite', () => {
    expect(PILOT_READINESS.map((p) => p.productId)).toContain('comptapilot')
    expect(PILOT_READINESS.find((p) => p.productId === 'comptapilot')?.readiness).toBe(
      'design_ready',
    )
    expect(PILOT_READINESS.find((p) => p.productId === 'salespilot')?.readiness).toBe(
      'partially_ready',
    )
  })
})

describe('E1.7 Design System 1.0', () => {
  it('exporte une version officielle unique', () => {
    expect(DESIGN_SYSTEM_NAME).toBe('ELFIS Design System')
    expect(VERSION).toBe('1.0.0')
    expect(BUILD).toBe('e1.7-ds-1.0.0')
    expect(DATE).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(MATURITY).toBe('stable')
    expect(DESIGN_SYSTEM_VERSION.version).toBe(VERSION)
    expect(DESIGN_SYSTEM_VERSION.build).toBe(BUILD)
  })

  it('matrice de certification cohérente', () => {
    expect(DESIGN_SYSTEM_CERTIFICATION.length).toBeGreaterThanOrEqual(12)
    const ids = DESIGN_SYSTEM_CERTIFICATION.map((r) => r.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const row of DESIGN_SYSTEM_CERTIFICATION) {
      expect(['ready', 'partially_ready', 'not_ready']).toContain(row.status)
      expect(row.justification.length).toBeGreaterThan(10)
    }
    const counts = certificationReadyCount()
    expect(counts.ready).toBeGreaterThanOrEqual(6)
    expect(counts.notReady).toBeGreaterThanOrEqual(1)
    expect(DESIGN_SYSTEM_CERTIFICATION.find((r) => r.id === 'legacy')?.status).toBe('not_ready')
    expect(DESIGN_SYSTEM_CERTIFICATION.find((r) => r.id === 'architecture')?.status).toBe('ready')
  })
})
