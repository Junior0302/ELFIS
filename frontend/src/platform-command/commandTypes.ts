/**
 * ELFIS Command Center V1 — types (UX only, Search Engine V1 for entities).
 */

export type CommandResultGroupId =
  | 'applications'
  | 'navigation'
  | 'clients'
  | 'documents'
  | 'factures'
  | 'prospects'
  | 'opportunites'
  | 'quick_actions'
  | 'commands'

export type CommandResultKind =
  | 'application'
  | 'navigation'
  | 'search'
  | 'quick_action'
  | 'command'

export type CommandResultItem = {
  id: string
  kind: CommandResultKind
  group: CommandResultGroupId
  title: string
  subtitle?: string
  href: string
  keywords?: readonly string[]
  /** Search Engine V1 resource_type when kind === 'search' */
  resourceType?: string
}

export type CommandResultGroup = {
  id: CommandResultGroupId
  label: string
  items: CommandResultItem[]
}

export type CommandModeState = {
  active: boolean
  /** Raw text after leading `>` */
  commandText: string
}

export type CommandSearchStatus = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

export type SearchEngineHit = {
  search_document_id: string
  resource_type: string
  resource_id: string
  title: string
  subtitle?: string | null
  snippet: string
  status?: string | null
  category?: string | null
  action_url?: string | null
  score: number
}
