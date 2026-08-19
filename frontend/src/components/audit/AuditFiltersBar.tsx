import type { AuditFilters, AuditPeriodHours } from '../../types/audit'

export type AuditFiltersBarValue = {
  hours: AuditPeriodHours
  useCustomRange: boolean
  date_from: string
  date_to: string
  category: string
  severity: string
  status: string
  action: string
  service: string
  product: string
  success: '' | 'true' | 'false'
  actor_email: string
  organization_id: string
  q: string
  target_type: string
  target_id: string
  correlation_id: string
  request_id: string
  actor_user_id: string
}

type Props = {
  value: AuditFiltersBarValue
  onChange: (next: AuditFiltersBarValue) => void
  onReset: () => void
  advancedOpen: boolean
  onAdvancedToggle: () => void
  disabled?: boolean
}

const PERIODS: Array<{ value: AuditPeriodHours; label: string }> = [
  { value: 1, label: '1 h' },
  { value: 24, label: '24 h' },
  { value: 168, label: '7 jours' },
  { value: 720, label: '30 jours' },
]

const CATEGORIES = ['', 'AUTH', 'IAM', 'SYSTEM', 'SECURITY', 'BILLING', 'JOB', 'EVENT', 'OTHER']
const SEVERITIES = ['', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
const STATUSES = ['', 'SUCCESS', 'FAILURE', 'PARTIAL']

export const DEFAULT_AUDIT_FILTERS: AuditFiltersBarValue = {
  hours: 24,
  useCustomRange: false,
  date_from: '',
  date_to: '',
  category: '',
  severity: '',
  status: '',
  action: '',
  service: '',
  product: '',
  success: '',
  actor_email: '',
  organization_id: '',
  q: '',
  target_type: '',
  target_id: '',
  correlation_id: '',
  request_id: '',
  actor_user_id: '',
}

export function filtersBarToApi(value: AuditFiltersBarValue, page: { limit: number; offset: number }): AuditFilters {
  const org = value.organization_id.trim()
  const orgId = org ? Number(org) : undefined
  const actorIdRaw = value.actor_user_id.trim()
  const actorId = actorIdRaw ? Number(actorIdRaw) : undefined
  const base: AuditFilters = {
    category: value.category || undefined,
    severity: value.severity || undefined,
    status: value.status || undefined,
    action: value.action.trim().toUpperCase() || undefined,
    service: value.service.trim() || undefined,
    product: value.product.trim() || undefined,
    success: value.success === '' ? undefined : value.success === 'true',
    actor_email: value.actor_email.trim() || undefined,
    organization_id: orgId != null && Number.isFinite(orgId) ? orgId : undefined,
    actor_user_id: actorId != null && Number.isFinite(actorId) ? actorId : undefined,
    q: value.q.trim() || undefined,
    target_type: value.target_type.trim() || undefined,
    target_id: value.target_id.trim() || undefined,
    correlation_id: value.correlation_id.trim() || undefined,
    request_id: value.request_id.trim() || undefined,
    limit: page.limit,
    offset: page.offset,
  }
  if (value.useCustomRange && (value.date_from || value.date_to)) {
    if (value.date_from) base.date_from = new Date(value.date_from).toISOString()
    if (value.date_to) base.date_to = new Date(value.date_to).toISOString()
  } else {
    base.hours = value.hours
  }
  return base
}

export default function AuditFiltersBar({
  value,
  onChange,
  onReset,
  advancedOpen,
  onAdvancedToggle,
  disabled,
}: Props) {
  const set = <K extends keyof AuditFiltersBarValue>(key: K, v: AuditFiltersBarValue[K]) => {
    onChange({ ...value, [key]: v })
  }

  return (
    <form
      className="audit-filters"
      onSubmit={(e) => e.preventDefault()}
      aria-label="Filtres Activity Center"
    >
      <label>
        Période
        <select
          value={value.hours}
          disabled={disabled || value.useCustomRange}
          onChange={(e) => set('hours', Number(e.target.value) as AuditPeriodHours)}
        >
          {PERIODS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <label className="audit-check">
        <input
          type="checkbox"
          checked={value.useCustomRange}
          disabled={disabled}
          onChange={(e) => set('useCustomRange', e.target.checked)}
        />
        Plage personnalisée
      </label>
      {value.useCustomRange && (
        <>
          <label>
            Début
            <input
              type="datetime-local"
              value={value.date_from}
              disabled={disabled}
              onChange={(e) => set('date_from', e.target.value)}
            />
          </label>
          <label>
            Fin
            <input
              type="datetime-local"
              value={value.date_to}
              disabled={disabled}
              onChange={(e) => set('date_to', e.target.value)}
            />
          </label>
        </>
      )}
      <label>
        Catégorie
        <select value={value.category} disabled={disabled} onChange={(e) => set('category', e.target.value)}>
          {CATEGORIES.map((c) => (
            <option key={c || 'all'} value={c}>
              {c || 'Toutes'}
            </option>
          ))}
        </select>
      </label>
      <label>
        Sévérité
        <select value={value.severity} disabled={disabled} onChange={(e) => set('severity', e.target.value)}>
          {SEVERITIES.map((s) => (
            <option key={s || 'all'} value={s}>
              {s || 'Toutes'}
            </option>
          ))}
        </select>
      </label>
      <label>
        Statut
        <select value={value.status} disabled={disabled} onChange={(e) => set('status', e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s || 'all'} value={s}>
              {s || 'Tous'}
            </option>
          ))}
        </select>
      </label>
      <label>
        Succès
        <select
          value={value.success}
          disabled={disabled}
          onChange={(e) => set('success', e.target.value as AuditFiltersBarValue['success'])}
        >
          <option value="">Tous</option>
          <option value="true">Succès</option>
          <option value="false">Échec</option>
        </select>
      </label>
      <label>
        Recherche
        <input
          type="search"
          value={value.q}
          disabled={disabled}
          placeholder="action, message, email…"
          maxLength={64}
          onChange={(e) => set('q', e.target.value)}
        />
      </label>

      <div className="audit-filters-actions">
        <button type="button" className="platform-btn" disabled={disabled} onClick={onAdvancedToggle}>
          {advancedOpen ? 'Masquer avancé' : 'Recherche avancée'}
        </button>
        <button type="button" className="platform-btn" disabled={disabled} onClick={onReset}>
          Réinitialiser
        </button>
      </div>

      {advancedOpen && (
        <div className="audit-filters-advanced" role="region" aria-label="Recherche avancée">
          <label>
            Action
            <input
              type="text"
              value={value.action}
              disabled={disabled}
              placeholder="LOGIN_SUCCESS"
              maxLength={128}
              onChange={(e) => set('action', e.target.value)}
            />
          </label>
          <label>
            Acteur (email)
            <input
              type="email"
              value={value.actor_email}
              disabled={disabled}
              maxLength={255}
              onChange={(e) => set('actor_email', e.target.value)}
            />
          </label>
          <label>
            Acteur (id)
            <input
              type="number"
              value={value.actor_user_id}
              disabled={disabled}
              onChange={(e) => set('actor_user_id', e.target.value)}
            />
          </label>
          <label>
            Organisation
            <input
              type="number"
              value={value.organization_id}
              disabled={disabled}
              onChange={(e) => set('organization_id', e.target.value)}
            />
          </label>
          <label>
            Service
            <input
              type="text"
              value={value.service}
              disabled={disabled}
              maxLength={128}
              onChange={(e) => set('service', e.target.value)}
            />
          </label>
          <label>
            Produit
            <input
              type="text"
              value={value.product}
              disabled={disabled}
              maxLength={128}
              onChange={(e) => set('product', e.target.value)}
            />
          </label>
          <label>
            target_type
            <input
              type="text"
              value={value.target_type}
              disabled={disabled}
              maxLength={64}
              onChange={(e) => set('target_type', e.target.value)}
            />
          </label>
          <label>
            target_id
            <input
              type="text"
              value={value.target_id}
              disabled={disabled}
              maxLength={128}
              onChange={(e) => set('target_id', e.target.value)}
            />
          </label>
          <label>
            correlation_id
            <input
              type="text"
              value={value.correlation_id}
              disabled={disabled}
              maxLength={64}
              onChange={(e) => set('correlation_id', e.target.value)}
            />
          </label>
          <label>
            request_id
            <input
              type="text"
              value={value.request_id}
              disabled={disabled}
              maxLength={64}
              onChange={(e) => set('request_id', e.target.value)}
            />
          </label>
        </div>
      )}
    </form>
  )
}
