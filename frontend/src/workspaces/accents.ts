/**
 * Accents workspace officiels (maquette Espaces ELFIS).
 * Primary = CTA / item actif / tabs / focus.
 * Soft = fond léger. Dark = hover / contraste (anciens DEPARTMENT_ACCENTS).
 */

import type { WorkspaceAccentTokens, WorkspaceId } from './types'

export const WORKSPACE_ACCENTS = {
  finance: {
    primary: '#16A34A',
    soft: '#ECFDF5',
    dark: '#0B3D2E',
    cssVar: '--workspace-finance',
    softCssVar: '--workspace-finance-soft',
    darkCssVar: '--workspace-finance-dark',
  },
  commercial: {
    primary: '#2563EB',
    soft: '#EFF6FF',
    dark: '#1D4ED8',
    cssVar: '--workspace-commercial',
    softCssVar: '--workspace-commercial-soft',
    darkCssVar: '--workspace-commercial-dark',
  },
  documents: {
    primary: '#7C3AED',
    soft: '#F5F3FF',
    dark: '#6D28D9',
    cssVar: '--workspace-documents',
    softCssVar: '--workspace-documents-soft',
    darkCssVar: '--workspace-documents-dark',
  },
  rh: {
    primary: '#C2410C',
    soft: '#FFF7ED',
    dark: '#9A3412',
    cssVar: '--workspace-rh',
    softCssVar: '--workspace-rh-soft',
    darkCssVar: '--workspace-rh-dark',
  },
  analyse: {
    primary: '#0E7490',
    soft: '#ECFEFF',
    dark: '#155E75',
    cssVar: '--workspace-analyse',
    softCssVar: '--workspace-analyse-soft',
    darkCssVar: '--workspace-analyse-dark',
  },
  support: {
    primary: '#3730A3',
    soft: '#EEF2FF',
    dark: '#312E81',
    cssVar: '--workspace-support',
    softCssVar: '--workspace-support-soft',
    darkCssVar: '--workspace-support-dark',
  },
} as const satisfies Record<WorkspaceId, WorkspaceAccentTokens>

/** Alias primaires pour DEPARTMENT_ACCENTS / surfaces hors shell. */
export const WORKSPACE_PRIMARY = {
  finance: WORKSPACE_ACCENTS.finance.primary,
  commercial: WORKSPACE_ACCENTS.commercial.primary,
  documents: WORKSPACE_ACCENTS.documents.primary,
  hr: WORKSPACE_ACCENTS.rh.primary,
  analyse: WORKSPACE_ACCENTS.analyse.primary,
  support: WORKSPACE_ACCENTS.support.primary,
} as const

/** Déclarations CSS à injecter (Phase 3+ shell). */
export function workspaceAccentCssDeclarations(id: WorkspaceId): string {
  const t = WORKSPACE_ACCENTS[id]
  return [
    `${t.cssVar}: ${t.primary};`,
    `${t.softCssVar}: ${t.soft};`,
    `${t.darkCssVar}: ${t.dark};`,
  ].join(' ')
}

export function allWorkspaceAccentCssVars(): Record<string, string> {
  const out: Record<string, string> = {}
  for (const t of Object.values(WORKSPACE_ACCENTS)) {
    out[t.cssVar] = t.primary
    out[t.softCssVar] = t.soft
    out[t.darkCssVar] = t.dark
  }
  return out
}
