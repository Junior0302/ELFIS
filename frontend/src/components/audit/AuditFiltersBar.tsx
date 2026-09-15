import type { AuditPeriodHours } from '../../types/audit'
import { type AuditFiltersBarValue } from './auditFilters'

export type { AuditFiltersBarValue }

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
