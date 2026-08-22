/**
 * Config workspace Documents — sidebar minimale V1.
 * Route hub réelle : /platform/documents. Extensible pour futures feuilles.
 */

import { WORKSPACE_ACCENTS } from './accents'
import type { WorkspaceConfig } from './types'

export const documentsWorkspaceConfig: WorkspaceConfig = {
  id: 'documents',
  label: 'Documents',
  description: 'Centralisation et intelligence documentaire.',
  engineLabel: 'Moteur DocPilot',
  engineProductId: 'docpilot',
  icon: 'file-text',
  accent: WORKSPACE_ACCENTS.documents,
  rootPath: '/platform/documents',
  availability: 'available',
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
  navigationGroups: [
    {
      id: 'documents',
      label: 'Documents',
      to: '/platform/documents',
      iconKey: '/platform/documents',
      children: [
        {
          id: 'documents-overview',
          label: 'Vue d’ensemble',
          to: '/platform/documents',
          activePolicy: 'exact',
        },
        /* Extensibilité Phase ultérieure — ne pas ajouter sans route réelle :
         * Extraction IA, Propositions, Validations, Archives, Coffres, Partages, Corbeille, Automatisations
         */
      ],
    },
  ],
}
