/**
 * SalesPilot Relationship Workspace — routing helpers (S1.4).
 */
import { describe, expect, it } from 'vitest'
import {
  isWorkspaceEntity,
  parseWorkspaceTab,
  workspacePath,
  WORKSPACE_ENTITIES,
  WORKSPACE_TABS,
} from './salesWorkspace'

describe('SalesPilot workspace routing', () => {
  it('accepte les 4 entités unifiées', () => {
    expect(WORKSPACE_ENTITIES).toEqual(['lead', 'company', 'person', 'opportunity'])
    expect(isWorkspaceEntity('lead')).toBe(true)
    expect(isWorkspaceEntity('invoice')).toBe(false)
  })

  it('construit les chemins workspace', () => {
    expect(workspacePath('opportunity', 42)).toBe('/sales/workspace/opportunity/42')
    expect(workspacePath('company', 7, 'timeline')).toBe(
      '/sales/workspace/company/7?tab=timeline',
    )
  })

  it('expose les onglets unifiés', () => {
    expect(WORKSPACE_TABS.map((t) => t.id)).toEqual([
      'overview',
      'contacts',
      'opportunities',
      'activities',
      'tasks',
      'notes',
      'documents',
      'timeline',
    ])
    expect(parseWorkspaceTab('notes')).toBe('notes')
    expect(parseWorkspaceTab('unknown')).toBe('overview')
  })
})
