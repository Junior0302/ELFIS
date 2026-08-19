import { Link } from 'react-router-dom'

export type KpiTone = 'neutral' | 'ok' | 'warn' | 'danger'

type Props = {
  icon?: string
  title: string
  value: string | number | null | undefined
  period?: string
  /** Évolution réelle API uniquement — sinon omit / null → « Donnée indisponible » */
  trend?: string | null
  tone?: KpiTone
  href?: string
  unavailable?: boolean
}

function formatValue(value: string | number | null | undefined, unavailable?: boolean): string {
  if (unavailable || value === null || value === undefined) return 'Donnée indisponible'
  return String(value)
}

export default function PlatformKpiCard({
  icon,
  title,
  value,
  period,
  trend,
  tone = 'neutral',
  href,
  unavailable,
}: Props) {
  const body = (
    <>
      <header className="pc-kpi-head">
        {icon && (
          <span className="pc-kpi-icon" aria-hidden>
            {icon}
          </span>
        )}
        <span className="pc-kpi-title">{title}</span>
      </header>
      <p className={`pc-kpi-value${unavailable || value == null ? ' is-muted' : ''}`}>
        {formatValue(value, unavailable)}
      </p>
      <footer className="pc-kpi-foot">
        <span className="pc-kpi-period">{period || '—'}</span>
        <span className="pc-kpi-trend">
          {trend != null && trend !== '' ? trend : 'Donnée indisponible'}
        </span>
        <span className={`pc-kpi-tone pc-kpi-tone-${tone}`} aria-label={`État ${tone}`}>
          {tone === 'ok' ? 'OK' : tone === 'warn' ? 'Attention' : tone === 'danger' ? 'Critique' : 'Neutre'}
        </span>
      </footer>
    </>
  )

  if (href) {
    return (
      <Link to={href} className={`pc-kpi-card pc-kpi-${tone}`}>
        {body}
      </Link>
    )
  }
  return <article className={`pc-kpi-card pc-kpi-${tone}`}>{body}</article>
}
