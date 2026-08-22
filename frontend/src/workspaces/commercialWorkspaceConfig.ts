/**
 * Config workspace Commercial — base salesNavModel (stabilité).
 * Pas de liens cross-domaine vers Finance (devis/catalogue/factures).
 */

import { WORKSPACE_ACCENTS } from './accents'
import type { WorkspaceConfig } from './types'

export const commercialWorkspaceConfig: WorkspaceConfig = {
  id: 'commercial',
  label: 'Commercial',
  description: 'Ventes et relation client.',
  engineLabel: null,
  engineProductId: 'salespilot',
  icon: 'handshake',
  accent: WORKSPACE_ACCENTS.commercial,
  rootPath: '/sales',
  availability: 'available',
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
  navigationGroups: [
    {
      id: 'dashboard',
      label: 'Tableau de bord',
      to: '/sales',
      iconKey: '/sales',
      children: [],
    },
    {
      id: 'prospection',
      label: 'Prospection',
      to: '/sales/leads',
      iconKey: '/sales/leads',
      children: [
        { id: 'leads', label: 'Prospects', to: '/sales/leads' },
        { id: 'companies', label: 'Entreprises', to: '/sales/companies' },
        { id: 'contacts', label: 'Contacts', to: '/sales/contacts' },
        { id: 'import', label: 'Import', to: '/sales/import' },
      ],
    },
    {
      id: 'pipeline',
      label: 'Pipeline',
      to: '/sales/pipeline',
      iconKey: '/sales/pipeline',
      children: [
        {
          id: 'pipeline-overview',
          label: 'Vue d’ensemble',
          to: '/sales/pipeline',
          activePolicy: 'exact',
        },
        { id: 'proposals', label: 'Propositions', to: '/sales/proposals' },
      ],
    },
    {
      id: 'activites',
      label: 'Activités',
      to: '/sales/activities',
      iconKey: '/sales/activities',
      children: [
        {
          id: 'activities-overview',
          label: 'Vue d’ensemble',
          to: '/sales/activities',
          activePolicy: 'exact',
        },
        { id: 'calendar', label: 'Calendrier', to: '/sales/calendar' },
        { id: 'tasks', label: 'Tâches', to: '/sales/tasks' },
        { id: 'journal', label: 'Journal', to: '/sales/journal' },
      ],
    },
    {
      id: 'reporting',
      label: 'Reporting',
      to: '/sales/reports',
      iconKey: '/sales/reports',
      children: [
        {
          id: 'reports-overview',
          label: 'Vue d’ensemble',
          to: '/sales/reports',
          activePolicy: 'exact',
        },
        { id: 'intelligence', label: 'Performances', to: '/sales/intelligence' },
      ],
    },
    {
      id: 'clients',
      label: 'Clients',
      to: '/sales/companies',
      iconKey: '/sales/companies',
      children: [
        { id: 'clients-companies', label: 'Entreprises', to: '/sales/companies' },
        { id: 'clients-contacts', label: 'Contacts', to: '/sales/contacts' },
        {
          id: 'relations',
          label: 'Relations',
          to: '/platform/relations',
          badge: 'ELFIS',
        },
      ],
    },
    {
      id: 'parametres',
      label: 'Paramètres',
      to: '/sales/settings',
      iconKey: '/sales/settings',
      children: [{ id: 'settings-general', label: 'Général', to: '/sales/settings' }],
    },
  ],
}
