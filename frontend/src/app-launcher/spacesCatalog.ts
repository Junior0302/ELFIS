/**
 * Catalogue des espaces métier ELFIS — source de vérité UX hub.
 * Routes réelles uniquement ; pas de fausses pages.
 */

import type { SpaceDefinition, SpaceId } from './spaces.types'

/**
 * Mapping entrée existant :
 * Finance → /dashboard · Commercial → /sales (dashboard commercial)
 * Documents → /platform/documents · RH / Analyse / Support → pas encore
 */
export const ELFIS_SPACES: readonly SpaceDefinition[] = [
  {
    id: 'finance',
    title: 'Finance',
    description: 'Facturation, banque, TVA et pilotage comptable.',
    accent: '#0B3D2E',
    engineLabel: 'Moteur ComptaPilot',
    engineProductId: 'comptapilot',
    entryRoute: '/dashboard',
    shortcuts: [
      { id: 'facturation', label: 'Facturation', to: '/facturation' },
      { id: 'tva', label: 'TVA', to: '/tva' },
      { id: 'banque', label: 'Banque', to: '/banque' },
    ],
    searchAliases: [
      'facture',
      'facturation',
      'tva',
      'banque',
      'compta',
      'comptabilité',
      'trésorerie',
      'clôture',
      'devis',
      'finance',
    ],
    capabilities: ['Facturation', 'Banque', 'TVA'],
  },
  {
    id: 'commercial',
    title: 'Commercial',
    description: 'Pipeline, prospects et opportunités commerciales.',
    accent: '#1D4ED8',
    engineLabel: 'Moteur SalesPilot',
    engineProductId: 'salespilot',
    entryRoute: '/sales',
    shortcuts: [
      { id: 'pipeline', label: 'Pipeline', to: '/sales/pipeline' },
      { id: 'leads', label: 'Prospects', to: '/sales/leads' },
      { id: 'proposals', label: 'Propositions', to: '/sales/proposals' },
    ],
    searchAliases: [
      'pipeline',
      'crm',
      'prospect',
      'prospects',
      'opportunité',
      'opportunités',
      'proposition',
      'commercial',
      'vente',
      'sales',
    ],
    capabilities: ['Pipeline', 'CRM', 'Propositions'],
  },
  {
    id: 'documents',
    title: 'Documents',
    description: 'Coffre documentaire et flux partagés de l’entreprise.',
    accent: '#6D28D9',
    engineLabel: 'Moteur DocPilot',
    engineProductId: 'docpilot',
    entryRoute: '/platform/documents',
    shortcuts: [{ id: 'vault', label: 'Coffre', to: '/platform/documents' }],
    searchAliases: [
      'document',
      'documents',
      'coffre',
      'vault',
      'fichier',
      'ocr',
      'archive',
    ],
    capabilities: ['Coffre', 'Recherche', 'Classement'],
  },
  {
    id: 'rh',
    title: 'RH',
    description: 'Équipes, congés et processus ressources humaines.',
    accent: '#C2410C',
    engineLabel: 'Moteur HRPilot',
    engineProductId: 'hrpilot',
    entryRoute: null,
    shortcuts: [],
    searchAliases: ['rh', 'hr', 'équipe', 'équipes', 'congés', 'onboarding', 'collaborateur'],
    capabilities: ['Équipes', 'Congés', 'Onboarding'],
  },
  {
    id: 'analyse',
    title: 'Analyse',
    description: 'Tableaux de bord et insights transverses.',
    accent: '#0E7490',
    engineLabel: null,
    engineProductId: null,
    entryRoute: null,
    shortcuts: [],
    searchAliases: ['analyse', 'analytics', 'kpi', 'rapport', 'rapports', 'insight', 'insights'],
    capabilities: ['KPI', 'Rapports', 'Alertes'],
  },
  {
    id: 'support',
    title: 'Support',
    description: 'Tickets, priorités et relation client.',
    accent: '#3730A3',
    engineLabel: 'Moteur SupportPilot',
    engineProductId: 'supportpilot',
    entryRoute: null,
    shortcuts: [],
    searchAliases: ['support', 'ticket', 'tickets', 'sla', 'aide', 'service client'],
    capabilities: ['Tickets', 'SLA', 'Base de savoir'],
  },
] as const

export function getSpaceById(id: SpaceId): SpaceDefinition {
  const found = ELFIS_SPACES.find((s) => s.id === id)
  if (!found) throw new Error(`Unknown space: ${id}`)
  return found
}

export function getSpaceByProductId(
  productId: string | null | undefined,
): SpaceDefinition | null {
  if (!productId) return null
  return ELFIS_SPACES.find((s) => s.engineProductId === productId) ?? null
}

/** Routes d’entrée espaces + raccourcis connus (SPA). */
export function getSpaceKnownRoutes(): ReadonlySet<string> {
  const routes = new Set<string>()
  for (const space of ELFIS_SPACES) {
    if (space.entryRoute) routes.add(space.entryRoute)
    for (const sc of space.shortcuts) routes.add(sc.to)
  }
  return routes
}
