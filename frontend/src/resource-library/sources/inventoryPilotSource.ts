/**
 * InventoryPilotSource — stub F1.2.
 * Même contrat ResourceSource ; available: false jusqu’au branchement réel.
 * Ne pas inventer de stocks / fournisseurs / entrepôts.
 */

import type { ResourceListResult } from '../types'
import type { ResourceSource } from './resourceSource'

const EMPTY: ResourceListResult = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 40,
  hasMore: false,
}

export const inventoryPilotResourceSource: ResourceSource = {
  id: 'inventory_pilot',
  label: 'InventoryPilot',
  available: false,
  capabilities: {
    list: false,
    search: false,
    create: false,
    update: false,
    delete: false,
    duplicate: false,
    history: false,
    favorites: false,
    recents: false,
    mostUsed: false,
    import: false,
    packs: false,
  },
  async list() {
    return EMPTY
  },
  async search() {
    return []
  },
}
