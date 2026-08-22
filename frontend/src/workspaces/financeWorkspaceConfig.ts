/**
 * Config workspace Finance — navigation cible Phase 3+.
 * Routes réelles uniquement. Trésorerie → /finance (contextual, pas de route fictive).
 */

import { WORKSPACE_ACCENTS } from './accents'
import type { WorkspaceConfig } from './types'

export const financeWorkspaceConfig: WorkspaceConfig = {
  id: 'finance',
  label: 'Finance',
  description: 'Facturation, banque, TVA et pilotage comptable.',
  engineLabel: 'Moteur ComptaPilot',
  engineProductId: 'comptapilot',
  icon: 'chart-column',
  accent: WORKSPACE_ACCENTS.finance,
  rootPath: '/dashboard',
  availability: 'available',
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
  navigationGroups: [
    {
      id: 'dashboard',
      label: 'Tableau de bord',
      to: '/dashboard',
      iconKey: '/dashboard',
      permission: 'invoice.read',
      children: [],
    },
    {
      id: 'ventes',
      label: 'Facturation',
      to: '/facturation',
      iconKey: '/facturation',
      permission: 'invoice.read',
      children: [
        {
          id: 'facturation-overview',
          to: '/facturation',
          label: 'Vue d’ensemble',
          permission: 'invoice.read',
          activePolicy: 'exact',
        },
        {
          id: 'facturation-documents',
          to: '/facturation/documents',
          label: 'Documents',
          permission: 'invoice.read',
        },
        {
          id: 'devis',
          to: '/devis',
          label: 'Devis',
          permission: 'invoice.read',
        },
        {
          id: 'catalogue',
          to: '/catalogue',
          label: 'Catalogue',
          permission: 'invoice.read',
        },
        {
          id: 'activites',
          to: '/activites',
          label: 'Activité',
          permission: 'invoice.read',
        },
      ],
    },
    {
      id: 'pilotage',
      label: 'Finance',
      to: '/finance',
      iconKey: '/finance',
      permission: 'invoice.read',
      children: [
        {
          id: 'finance-overview',
          to: '/finance',
          label: 'Vue d’ensemble',
          permission: 'invoice.read',
          activePolicy: 'primary',
        },
        {
          id: 'tresorerie',
          to: '/finance',
          label: 'Trésorerie',
          permission: 'invoice.read',
          /** Même path que Vue d’ensemble — jamais actif en parallèle (Phase 2/3). */
          activePolicy: 'contextual',
        },
        {
          id: 'banque',
          to: '/banque',
          label: 'Banque',
          permission: 'bank.read',
        },
        {
          id: 'tva',
          to: '/tva',
          label: 'TVA',
          permission: 'invoice.read',
        },
        {
          id: 'cloture',
          to: '/cloture',
          label: 'Clôture',
          permission: 'invoice.read',
        },
        {
          id: 'cockpit',
          to: '/cockpit',
          label: 'Centre opérationnel',
          permission: 'invoice.read',
        },
        {
          id: 'reports',
          to: '/reports',
          label: 'Rapports',
          permission: 'invoice.read',
        },
      ],
    },
    {
      id: 'comptabilite',
      label: 'Comptabilité',
      to: '/accounting',
      iconKey: '/accounting',
      permission: 'ai.analysis',
      children: [
        {
          id: 'accounting-hub',
          to: '/accounting',
          label: 'Vue d’ensemble',
          permission: 'ai.analysis',
          activePolicy: 'exact',
        },
        {
          id: 'accounting-proposals',
          to: '/accounting/proposals',
          label: 'Propositions',
          permission: 'ai.analysis',
        },
        {
          id: 'accounting-engine',
          to: '/accounting/engine',
          label: 'Journaux',
          permission: 'ai.analysis',
        },
        {
          id: 'history',
          to: '/history',
          label: 'Historique',
          permission: 'invoice.read',
        },
      ],
    },
    {
      id: 'documents',
      label: 'Documents comptables',
      to: '/documents',
      iconKey: '/documents',
      permission: 'documents.read',
      children: [
        {
          id: 'documents-list',
          to: '/documents',
          label: 'Documents comptables',
          permission: 'documents.read',
          activePolicy: 'exact',
        },
        {
          id: 'deposit',
          to: '/deposit',
          label: 'Importer',
          permission: 'invoice.create',
        },
        {
          id: 'migration',
          to: '/migration',
          label: 'Centre d’import',
          permission: 'migration_center.read',
        },
      ],
    },
    {
      id: 'tiers',
      label: 'Clients & fournisseurs',
      to: '/clients',
      iconKey: '/clients',
      permission: 'invoice.read',
      children: [
        { id: 'clients', to: '/clients', label: 'Clients', permission: 'invoice.read' },
        {
          id: 'fournisseurs',
          to: '/fournisseurs',
          label: 'Fournisseurs',
          permission: 'invoice.read',
        },
      ],
    },
    {
      id: 'assistant',
      label: 'Assistance',
      to: '/copilote',
      iconKey: '/copilote',
      permission: 'ai.analysis',
      children: [
        { id: 'copilote', to: '/copilote', label: 'Assistant financier', permission: 'ai.analysis' },
        { id: 'signaux', to: '/intelligence', label: 'Signaux', permission: 'ai.analysis' },
        {
          id: 'aura',
          to: '/platform/aura',
          label: 'Aura',
          permission: 'ai.analysis',
          badge: 'ELFIS',
        },
      ],
    },
    {
      id: 'parametres',
      label: 'Paramètres',
      to: '/settings',
      iconKey: '/settings',
      children: [{ id: 'settings', to: '/settings', label: 'Paramètres Finance' }],
    },
  ],
}
