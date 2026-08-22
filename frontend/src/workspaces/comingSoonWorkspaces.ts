/**
 * Espaces roadmap (launcher « Bientôt ») — pas de navigation métier.
 */

import { WORKSPACE_ACCENTS } from './accents'
import type { WorkspaceConfig } from './types'

export const rhWorkspaceConfig: WorkspaceConfig = {
  id: 'rh',
  label: 'RH',
  description: 'Équipes, congés et processus ressources humaines.',
  engineLabel: 'Moteur HRPilot',
  engineProductId: 'hrpilot',
  icon: 'users',
  accent: WORKSPACE_ACCENTS.rh,
  rootPath: null,
  availability: 'coming_soon',
  shortcuts: [],
  searchAliases: ['rh', 'hr', 'équipe', 'équipes', 'congés', 'onboarding', 'collaborateur'],
  capabilities: ['Équipes', 'Congés', 'Onboarding'],
  navigationGroups: [],
}

export const analyseWorkspaceConfig: WorkspaceConfig = {
  id: 'analyse',
  label: 'Analyse',
  description: 'Tableaux de bord et insights transverses.',
  engineLabel: null,
  engineProductId: null,
  icon: 'bar-chart-3',
  accent: WORKSPACE_ACCENTS.analyse,
  rootPath: null,
  availability: 'coming_soon',
  shortcuts: [],
  searchAliases: ['analyse', 'analytics', 'kpi', 'rapport', 'rapports', 'insight', 'insights'],
  capabilities: ['KPI', 'Rapports', 'Alertes'],
  navigationGroups: [],
}

export const supportWorkspaceConfig: WorkspaceConfig = {
  id: 'support',
  label: 'Support',
  description: 'Tickets, priorités et relation client.',
  engineLabel: 'Moteur SupportPilot',
  engineProductId: 'supportpilot',
  icon: 'life-buoy',
  accent: WORKSPACE_ACCENTS.support,
  rootPath: null,
  availability: 'coming_soon',
  shortcuts: [],
  searchAliases: ['support', 'ticket', 'tickets', 'sla', 'aide', 'service client'],
  capabilities: ['Tickets', 'SLA', 'Base de savoir'],
  navigationGroups: [],
}
