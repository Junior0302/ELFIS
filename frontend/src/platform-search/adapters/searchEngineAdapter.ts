/**
 * Adapters Search Engine V1 → SearchResult (aucune logique fuzzy FE).
 */

import type { SearchResult } from '../types'
import { mapEngineResourceType } from '../mapResourceType'

export type EngineHit = {
  search_document_id: string
  resource_type: string
  resource_id: string
  title: string
  subtitle?: string | null
  snippet?: string
  status?: string | null
  category?: string | null
  action_url?: string | null
  score?: number
  metadata?: Record<string, unknown>
}

export function engineHitToSearchResult(hit: EngineHit): SearchResult {
  const type = mapEngineResourceType(hit.resource_type)
  return {
    type,
    id: String(hit.resource_id || hit.search_document_id),
    title: hit.title || 'Sans titre',
    subtitle: hit.subtitle ?? undefined,
    description: hit.snippet || undefined,
    status: hit.status ?? null,
    route: hit.action_url ?? null,
    source: 'search_engine_v1',
    score: hit.score,
    metadata: {
      search_document_id: hit.search_document_id,
      resource_type: hit.resource_type,
      category: hit.category,
      ...(hit.metadata ?? {}),
    },
    actions: hit.action_url
      ? [{ id: 'open', label: 'Ouvrir', kind: 'navigate', href: hit.action_url }]
      : [{ id: 'select', label: 'Sélectionner', kind: 'select' }],
  }
}
