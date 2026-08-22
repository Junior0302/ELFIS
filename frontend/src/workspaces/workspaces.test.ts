/**
 * Phase 2 — Workspace Registry / accents / navigation policies.
 */

import { describe, expect, it } from 'vitest'
import { ELFIS_SPACES, getSpaceById, getSpaceByProductId } from '../app-launcher/spacesCatalog'
import { DEPARTMENT_ACCENTS } from '../design-system/colors/elfisBrandTokens'
import { getProductById } from '../design-system/products/registry'
import {
  WORKSPACE_ACCENTS,
  WORKSPACE_REGISTRY,
  assertWorkspaceEngineRegistered,
  commercialWorkspaceConfig,
  documentsWorkspaceConfig,
  financeWorkspaceConfig,
  getAvailableWorkspaces,
  getWorkspaceById,
  getWorkspaceByProductId,
  isWorkspaceNavLeafActive,
  workspaceToSpaceDefinition,
} from './index'

describe('workspaces Phase 2', () => {
  it('registry contient les 6 espaces launcher', () => {
    expect(WORKSPACE_REGISTRY.map((w) => w.id)).toEqual([
      'finance',
      'commercial',
      'documents',
      'rh',
      'analyse',
      'support',
    ])
  })

  it('accents officiels maquette', () => {
    expect(WORKSPACE_ACCENTS.finance.primary).toBe('#16A34A')
    expect(WORKSPACE_ACCENTS.commercial.primary).toBe('#2563EB')
    expect(WORKSPACE_ACCENTS.documents.primary).toBe('#7C3AED')
    expect(DEPARTMENT_ACCENTS.finance).toBe('#16A34A')
    expect(DEPARTMENT_ACCENTS.commercial).toBe('#2563EB')
    expect(DEPARTMENT_ACCENTS.documents).toBe('#7C3AED')
  })

  it('ELFIS_SPACES dérivé du workspace registry', () => {
    expect(ELFIS_SPACES).toHaveLength(6)
    expect(getSpaceById('finance').accent).toBe('#16A34A')
    expect(getSpaceById('commercial').accent).toBe('#2563EB')
    expect(getSpaceById('documents').accent).toBe('#7C3AED')
    expect(getSpaceById('finance').entryRoute).toBe('/dashboard')
    expect(getSpaceById('commercial').entryRoute).toBe('/sales')
    expect(getSpaceById('documents').entryRoute).toBe('/platform/documents')
  })

  it('engineProductId compose Product Registry', () => {
    expect(getWorkspaceByProductId('comptapilot')?.id).toBe('finance')
    expect(getSpaceByProductId('salespilot')?.id).toBe('commercial')
    expect(assertWorkspaceEngineRegistered(financeWorkspaceConfig)).toBe(true)
    expect(getProductById('comptapilot').id).toBe('comptapilot')
  })

  it('Finance — Trésorerie contextual sur /finance', () => {
    const group = financeWorkspaceConfig.navigationGroups.find((g) => g.id === 'pilotage')
    expect(group).toBeTruthy()
    const overview = group!.children.find((c) => c.id === 'finance-overview')!
    const tresorerie = group!.children.find((c) => c.id === 'tresorerie')!
    expect(overview.to).toBe('/finance')
    expect(tresorerie.to).toBe('/finance')
    expect(tresorerie.activePolicy).toBe('contextual')
    expect(isWorkspaceNavLeafActive(overview, '/finance', group!.children)).toBe(true)
    expect(isWorkspaceNavLeafActive(tresorerie, '/finance', group!.children)).toBe(false)
  })

  it('Commercial — pas de liens cross-domaine devis/catalogue/factures', () => {
    const tos = commercialWorkspaceConfig.navigationGroups.flatMap((g) => [
      g.to,
      ...g.children.map((c) => c.to),
    ])
    expect(tos.some((t) => t === '/devis' || t === '/catalogue' || t.startsWith('/facturation'))).toBe(
      false,
    )
    expect(tos.every((t) => t.startsWith('/sales') || t.startsWith('/platform/'))).toBe(true)
  })

  it('Documents — sidebar minimale hub uniquement', () => {
    const leaves = documentsWorkspaceConfig.navigationGroups.flatMap((g) => g.children)
    expect(leaves.map((l) => l.to)).toEqual(['/platform/documents'])
    expect(documentsWorkspaceConfig.rootPath).toBe('/platform/documents')
  })

  it('coming_soon sans rootPath', () => {
    const soon = WORKSPACE_REGISTRY.filter((w) => w.availability === 'coming_soon')
    expect(soon.every((w) => w.rootPath === null)).toBe(true)
    expect(getAvailableWorkspaces().map((w) => w.id)).toEqual([
      'finance',
      'commercial',
      'documents',
    ])
  })

  it('adapter SpaceDefinition conserve label/description', () => {
    const space = workspaceToSpaceDefinition(getWorkspaceById('finance'))
    expect(space.title).toBe('Finance')
    expect(space.engineProductId).toBe('comptapilot')
  })
})
