/**
 * Actions Resource Card — disponibles selon capabilities source.
 */

import type { Resource, ResourceActionDef } from './types'
import type { ResourceSource } from './sources/resourceSource'

export function getResourceActions(source: ResourceSource, _resource?: Resource): ResourceActionDef[] {
  return [
    {
      id: 'add',
      label: 'Ajouter',
      available: true,
    },
    {
      id: 'edit',
      label: 'Modifier',
      available: source.capabilities.update,
      disabledReason: source.capabilities.update
        ? undefined
        : 'Modification non supportée par la source',
    },
    {
      id: 'duplicate',
      label: 'Dupliquer',
      available: source.capabilities.duplicate,
      disabledReason: source.capabilities.duplicate
        ? undefined
        : 'Duplication non supportée par la source',
    },
    {
      id: 'view',
      label: 'Voir',
      available: true,
    },
    {
      id: 'history',
      label: 'Historique',
      available: source.capabilities.history,
      disabledReason: 'Historique d’utilisation non exposé (API absente)',
    },
  ]
}

export type { ResourceActionDef }
