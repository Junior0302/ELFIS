/**
 * ResourceSource — abstraction officielle Smart Library / ProductPicker.
 * Les consommateurs UI ne voient jamais l’implémentation concrète.
 */

import type {
  Resource,
  ResourceCreateInput,
  ResourceListResult,
  ResourceQuery,
  ResourceSourceId,
  ResourceUpdateInput,
} from '../types'

export type ResourceSource = {
  id: ResourceSourceId
  label: string
  /** false = stub / non branché — ne pas utiliser comme source active. */
  available: boolean
  capabilities: {
    list: boolean
    search: boolean
    create: boolean
    update: boolean
    delete: boolean
    duplicate: boolean
    history: boolean
    favorites: boolean
    recents: boolean
    mostUsed: boolean
    import: boolean
    packs: boolean
  }
  list: (query: ResourceQuery) => Promise<ResourceListResult>
  get?: (id: string, token: string, orgId?: number | null) => Promise<Resource | null>
  create?: (input: ResourceCreateInput, token: string, orgId?: number | null) => Promise<Resource>
  update?: (
    id: string,
    input: ResourceUpdateInput,
    token: string,
    orgId?: number | null,
  ) => Promise<Resource>
  delete?: (id: string, token: string, orgId?: number | null) => Promise<void>
  /** Recherche légère (picker) — défaut = list filtrée. */
  search?: (query: ResourceQuery) => Promise<Resource[]>
}

export function assertSourceAvailable(source: ResourceSource): void {
  if (!source.available) {
    throw new Error(`ResourceSource « ${source.id} » non disponible`)
  }
}
