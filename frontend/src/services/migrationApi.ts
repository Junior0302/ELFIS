export type MigrationMode = 'initial_migration' | 'one_time_import'

export type MigrationStatus =
  | 'draft'
  | 'profile_completed'
  | 'sources_selected'
  | 'awaiting_upload'
  | 'cancelled'
  | string

export type CompanyProfile = {
  company_age_range: string
  legal_form: string
  team_size: string
  accountant_status: string
  join_reasons: string[]
  other_legal_form?: string | null
  other_join_reason?: string | null
  answers_metadata?: Record<string, unknown> | null
}

export type MigrationProgress = {
  schema_version: number
  overall_percent: number
  current_step: string
  current_step_percent: number
  completed_steps: string[]
  pending_steps: string[]
  blocked_steps: string[]
  warnings: string[]
  estimated_remaining_seconds: number | null
  updated_at?: string | null
}

export type MigrationSession = {
  id: string
  migration_session_token?: string
  organization_id: number
  created_by_user_id?: number | null
  mode: MigrationMode | string
  status: MigrationStatus
  current_step: number
  company_profile?: CompanyProfile | null
  migration_profile?: { schema_version: number; data: Record<string, unknown> } | null
  ai_profile?: { schema_version: number; data: Record<string, unknown> } | null
  selected_sources?: string[] | null
  configuration?: Record<string, unknown> | null
  progress?: MigrationProgress | Record<string, unknown> | null
  answers_metadata?: Record<string, unknown> | null
  version: number
  started_at?: string | null
  last_activity_at?: string | null
  completed_at?: string | null
  cancelled_at?: string | null
  cancel_reason?: string | null
  created_at?: string | null
  updated_at?: string | null
  timeline?: MigrationTimelineEntry[]
  recent_activities?: MigrationActivity[]
}

export type MigrationTimelineEntry = {
  id: string
  step_key: string
  step_order: number
  status: string
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
}

export type MigrationActivity = {
  id: string
  activity_type: string
  title: string
  description?: string | null
  severity: string
  occurred_at?: string | null
}

export type SourceCatalogItem = {
  id: string
  label: string
  category: string
  availability:
    | 'available'
    | 'coming_soon'
    | 'unavailable'
    | 'beta'
    | 'deprecated'
    | 'maintenance'
    | string
  accepted_formats: string[]
  description: string
  capabilities?: string[]
  requires_connection?: boolean
  supports_folder?: boolean
  supports_incremental_import?: boolean
  supports_preview?: boolean
  metadata?: Record<string, unknown>
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

function headers(token: string, orgId?: number | null): HeadersInit {
  const h: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
  if (orgId != null) h['X-Organization-Id'] = String(orgId)
  return h
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = text
  }
  if (!res.ok) {
    const detail = (body as { detail?: unknown })?.detail
    const msg =
      typeof detail === 'string'
        ? detail
        : detail && typeof detail === 'object' && 'message' in (detail as object)
          ? String((detail as { message: string }).message)
          : `Erreur API ${res.status}`
    const code =
      detail && typeof detail === 'object' && 'code' in (detail as object)
        ? String((detail as { code: string }).code)
        : undefined
    const err = new Error(msg) as Error & { code?: string; status?: number }
    err.code = code
    err.status = res.status
    throw err
  }
  return body as T
}

export const migrationApi = {
  async listSessions(token: string, orgId: number, params?: { limit?: number; offset?: number }) {
    const q = new URLSearchParams()
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.offset) q.set('offset', String(params.offset))
    const qs = q.toString()
    const res = await fetch(`${apiRoot()}/migrations/sessions${qs ? `?${qs}` : ''}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: MigrationSession[]; total: number }>(res)
  },

  async getSession(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}`, {
      headers: headers(token, orgId),
    })
    return parse<MigrationSession>(res)
  },

  async createSession(token: string, orgId: number, mode: MigrationMode) {
    const res = await fetch(`${apiRoot()}/migrations/sessions`, {
      method: 'POST',
      headers: headers(token, orgId),
      body: JSON.stringify({ mode }),
    })
    return parse<MigrationSession>(res)
  },

  async patchProfile(
    token: string,
    orgId: number,
    sessionId: string,
    profile: CompanyProfile,
    version?: number,
  ) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/profile`, {
      method: 'PATCH',
      headers: headers(token, orgId),
      body: JSON.stringify({ profile, version }),
    })
    return parse<MigrationSession>(res)
  },

  async patchSources(
    token: string,
    orgId: number,
    sessionId: string,
    sourceIds: string[],
    version?: number,
  ) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/sources`, {
      method: 'PATCH',
      headers: headers(token, orgId),
      body: JSON.stringify({ source_ids: sourceIds, version }),
    })
    return parse<MigrationSession>(res)
  },

  async continueSession(token: string, orgId: number, sessionId: string, version?: number) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/continue`, {
      method: 'POST',
      headers: headers(token, orgId),
      body: JSON.stringify({ version }),
    })
    return parse<MigrationSession>(res)
  },

  async cancelSession(token: string, orgId: number, sessionId: string, version?: number) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/cancel`, {
      method: 'POST',
      headers: headers(token, orgId),
      body: JSON.stringify({ version }),
    })
    return parse<MigrationSession>(res)
  },

  async resumeSession(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/resume`, {
      method: 'POST',
      headers: headers(token, orgId),
      body: JSON.stringify({}),
    })
    return parse<MigrationSession>(res)
  },

  async getTimeline(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/timeline`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: MigrationTimelineEntry[] }>(res)
  },

  async getActivities(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/activities`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: MigrationActivity[] }>(res)
  },

  async getProgress(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/migrations/sessions/${sessionId}/progress`, {
      headers: headers(token, orgId),
    })
    return parse<{ progress: MigrationProgress }>(res)
  },

  async sourceCatalog(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/migrations/source-catalog`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: SourceCatalogItem[] }>(res)
  },
}

export const MIGRATION_SESSION_LS_KEY = 'elfis_migration_current_session_id'

export function buildCompanySummary(profile: CompanyProfile): string {
  const age: Record<string, string> = {
    starting_today: 'en création',
    less_than_6_months: 'créée il y a moins de 6 mois',
    between_6_months_and_2_years: 'créée entre 6 mois et 2 ans',
    more_than_2_years: 'créée il y a plus de deux ans',
  }
  const form: Record<string, string> = {
    micro_enterprise: 'micro-entreprise',
    sole_proprietorship: 'entreprise individuelle',
    eurl: 'EURL',
    sarl: 'SARL',
    sasu: 'SASU',
    sas: 'SAS',
    association: 'association',
    other: profile.other_legal_form || 'forme juridique autre',
  }
  const team: Record<string, string> = {
    one: 'une personne',
    two_to_five: 'une petite équipe',
    six_to_twenty: 'une équipe de taille moyenne',
    more_than_twenty: 'une équipe élargie',
  }
  const accountant: Record<string, string> = {
    has_accountant: 'avec un cabinet comptable',
    no_accountant: 'sans expert-comptable',
    looking_for_accountant: 'en recherche d’expert-comptable',
  }
  return `Nous avons identifié que vous êtes une ${form[profile.legal_form] || profile.legal_form} ${age[profile.company_age_range] || ''}, avec ${team[profile.team_size] || 'votre équipe'} ${accountant[profile.accountant_status] || ''}. La migration sera adaptée à votre situation.`
}

export function validateProfileClient(profile: Partial<CompanyProfile>): string | null {
  if (!profile.company_age_range) return 'Indiquez l’ancienneté de l’entreprise.'
  if (!profile.legal_form) return 'Indiquez le statut juridique.'
  if (profile.legal_form === 'other' && !(profile.other_legal_form || '').trim()) {
    return 'Précisez la forme juridique.'
  }
  if (!profile.team_size) return 'Indiquez la taille de l’équipe.'
  if (!profile.accountant_status) return 'Indiquez votre situation comptable.'
  if (!profile.join_reasons?.length) return 'Sélectionnez au moins une raison.'
  if (profile.join_reasons.includes('other') && !(profile.other_join_reason || '').trim()) {
    return 'Précisez la raison « autre ».'
  }
  return null
}

export function canCancelStatus(status: string): boolean {
  return ['draft', 'profile_completed', 'sources_selected', 'awaiting_upload'].includes(status)
}

export function canResumeStatus(status: string): boolean {
  return !['cancelled', 'completed', 'failed'].includes(status)
}

export function isSourceSelectable(availability: string): boolean {
  return availability === 'available' || availability === 'beta'
}

export function sourceAvailabilityBadge(availability: string): string | null {
  switch (availability) {
    case 'beta':
      return 'Bêta'
    case 'coming_soon':
      return 'Bientôt disponible'
    case 'maintenance':
      return 'Maintenance'
    case 'deprecated':
      return 'Ancienne intégration'
    default:
      return null
  }
}

export function progressPercent(session: MigrationSession | null | undefined): number | null {
  const p = session?.progress
  if (!p || typeof p !== 'object') return null
  if ('overall_percent' in p && typeof (p as MigrationProgress).overall_percent === 'number') {
    return (p as MigrationProgress).overall_percent
  }
  return null
}

export const STEP_LABELS: Record<string, string> = {
  welcome: 'Bienvenue',
  company_profile: 'Profil entreprise',
  data_sources: 'Sources',
  upload_preparation: 'Préparation dépôt',
  file_upload: 'Dépôt',
  analysis: 'Analyse',
  validation: 'Validation',
  import: 'Import',
  completion: 'Terminé',
}
