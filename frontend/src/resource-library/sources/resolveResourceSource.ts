/**
 * Résolution de source Resource — LocalLibrary V1, InventoryPilot stub.
 */

import { inventoryPilotResourceSource } from './inventoryPilotSource'
import { localLibrarySource } from './localLibrarySource'
import type { ResourceSource } from './resourceSource'
import type { ResourceSourceId } from '../types'

export function resolveResourceSource(
  prefer: ResourceSourceId = 'local_library',
): ResourceSource {
  if (prefer === 'inventory_pilot' && inventoryPilotResourceSource.available) {
    return inventoryPilotResourceSource
  }
  return localLibrarySource
}

/** Source active officielle Smart Library V1. */
export function getActiveResourceSource(): ResourceSource {
  return resolveResourceSource('local_library')
}

export { localLibrarySource } from './localLibrarySource'
export { inventoryPilotResourceSource } from './inventoryPilotSource'
export type { ResourceSource } from './resourceSource'
