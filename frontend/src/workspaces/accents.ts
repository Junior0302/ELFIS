/**
 * Accents workspace officiels (maquette Espaces métiers – Icônes Lucide).
 * Primary = CTA / item actif / tabs / focus.
 * Soft = fond pastel. Dark = hover / contraste.
 */

import type { WorkspaceAccentTokens, WorkspaceId } from './types'

export const WORKSPACE_ACCENTS = {
  finance: {
    primary: '#16A34A',
    soft: '#ECFDF5',
    dark: '#15803D',
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
  achats: {
    primary: '#F59E0B',
    soft: '#FFFBEB',
    dark: '#D97706',
    cssVar: '--workspace-achats',
    softCssVar: '--workspace-achats-soft',
    darkCssVar: '--workspace-achats-dark',
  },
  stock: {
    primary: '#EC4899',
    soft: '#FDF2F8',
    dark: '#DB2777',
    cssVar: '--workspace-stock',
    softCssVar: '--workspace-stock-soft',
    darkCssVar: '--workspace-stock-dark',
  },
  logistique: {
    primary: '#14B8A6',
    soft: '#F0FDFA',
    dark: '#0D9488',
    cssVar: '--workspace-logistique',
    softCssVar: '--workspace-logistique-soft',
    darkCssVar: '--workspace-logistique-dark',
  },
  rh: {
    primary: '#F97316',
    soft: '#FFF7ED',
    dark: '#EA580C',
    cssVar: '--workspace-rh',
    softCssVar: '--workspace-rh-soft',
    darkCssVar: '--workspace-rh-dark',
  },
  planning: {
    primary: '#06B6D4',
    soft: '#ECFEFF',
    dark: '#0891B2',
    cssVar: '--workspace-planning',
    softCssVar: '--workspace-planning-soft',
    darkCssVar: '--workspace-planning-dark',
  },
  projets: {
    primary: '#EF4444',
    soft: '#FEF2F2',
    dark: '#DC2626',
    cssVar: '--workspace-projets',
    softCssVar: '--workspace-projets-soft',
    darkCssVar: '--workspace-projets-dark',
  },
  banque: {
    primary: '#059669',
    soft: '#ECFDF5',
    dark: '#047857',
    cssVar: '--workspace-banque',
    softCssVar: '--workspace-banque-soft',
    darkCssVar: '--workspace-banque-dark',
  },
  comptabilite: {
    primary: '#6366F1',
    soft: '#EEF2FF',
    dark: '#4F46E5',
    cssVar: '--workspace-comptabilite',
    softCssVar: '--workspace-comptabilite-soft',
    darkCssVar: '--workspace-comptabilite-dark',
  },
  facturation: {
    primary: '#EAB308',
    soft: '#FEFCE8',
    dark: '#CA8A04',
    cssVar: '--workspace-facturation',
    softCssVar: '--workspace-facturation-soft',
    darkCssVar: '--workspace-facturation-dark',
  },
  conformite: {
    primary: '#3B82F6',
    soft: '#EFF6FF',
    dark: '#2563EB',
    cssVar: '--workspace-conformite',
    softCssVar: '--workspace-conformite-soft',
    darkCssVar: '--workspace-conformite-dark',
  },
  rse: {
    primary: '#22C55E',
    soft: '#F0FDF4',
    dark: '#16A34A',
    cssVar: '--workspace-rse',
    softCssVar: '--workspace-rse-soft',
    darkCssVar: '--workspace-rse-dark',
  },
  parametres: {
    primary: '#6B7280',
    soft: '#F9FAFB',
    dark: '#4B5563',
    cssVar: '--workspace-parametres',
    softCssVar: '--workspace-parametres-soft',
    darkCssVar: '--workspace-parametres-dark',
  },
} as const satisfies Record<WorkspaceId, WorkspaceAccentTokens>

/** Alias primaires pour DEPARTMENT_ACCENTS / surfaces hors shell. */
export const WORKSPACE_PRIMARY = {
  finance: WORKSPACE_ACCENTS.finance.primary,
  commercial: WORKSPACE_ACCENTS.commercial.primary,
  documents: WORKSPACE_ACCENTS.documents.primary,
  achats: WORKSPACE_ACCENTS.achats.primary,
  stock: WORKSPACE_ACCENTS.stock.primary,
  logistique: WORKSPACE_ACCENTS.logistique.primary,
  hr: WORKSPACE_ACCENTS.rh.primary,
  planning: WORKSPACE_ACCENTS.planning.primary,
  projets: WORKSPACE_ACCENTS.projets.primary,
  banque: WORKSPACE_ACCENTS.banque.primary,
  comptabilite: WORKSPACE_ACCENTS.comptabilite.primary,
  facturation: WORKSPACE_ACCENTS.facturation.primary,
  conformite: WORKSPACE_ACCENTS.conformite.primary,
  rse: WORKSPACE_ACCENTS.rse.primary,
  parametres: WORKSPACE_ACCENTS.parametres.primary,
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
