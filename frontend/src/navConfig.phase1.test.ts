import { describe, expect, it } from 'vitest'
import { findNavItem, navSections, PHASE1_INTEGRATED_PATHS } from './navConfig'

describe('Frontend Integration Phase 1 — navigation', () => {
  it('expose les entrées mission dans la sidebar', () => {
    const tos = navSections.flatMap((s) => s.items.map((i) => i.to))
    expect(tos).toContain('/dashboard')
    expect(tos).toContain('/documents')
    expect(tos).toContain('/migration')
    expect(tos).toContain('/accounting')
    expect(tos).toContain('/accounting/intelligence')
    expect(tos).toContain('/search')
    expect(tos).toContain('/notifications')
    expect(tos).toContain('/reports')
    expect(tos).toContain('/admin/equipe')
    expect(tos).toContain('/cockpit')
    expect(tos).toContain('/settings')
  })

  it('préfère le match de route le plus spécifique', () => {
    const item = findNavItem('/accounting/intelligence')
    expect(item?.to).toBe('/accounting/intelligence')
  })

  it('liste les chemins intégrés Phase 1', () => {
    expect(PHASE1_INTEGRATED_PATHS.length).toBeGreaterThan(10)
    expect(PHASE1_INTEGRATED_PATHS).toContain('/accounting')
    expect(PHASE1_INTEGRATED_PATHS).toContain('/cockpit')
  })

  it('chaque item a un guide de 4 phrases', () => {
    for (const section of navSections) {
      for (const item of section.items) {
        expect(item.guide).toHaveLength(4)
        if (item.guideLocked) expect(item.guideLocked).toHaveLength(4)
      }
    }
  })

  it('Accueil propose un guideLocked onboarding sans KPI', () => {
    const home = navSections.flatMap((s) => s.items).find((i) => i.to === '/dashboard')
    expect(home?.guideLocked).toBeDefined()
    expect(home!.guideLocked!.join(' ')).not.toMatch(/Health Score/i)
    expect(home!.guideLocked!.join(' ')).toMatch(/essai/i)
  })
})
