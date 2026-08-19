/**
 * Graphiques FCC — patterns SVG alignés sur FinancialDashboardPage,
 * sans modifier la logique métier /finance. Données = overview.charts uniquement.
 */
import { formatEuro } from '../../services/financialApi'

export function fmtChartPeriod(period: string): string {
  const monthMatch = /^(\d{4})-(\d{2})$/.exec(period)
  if (monthMatch) {
    const d = new Date(Number(monthMatch[1]), Number(monthMatch[2]) - 1, 1)
    return d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
  }
  const weekMatch = /^\d{4}-(S\d{2})$/.exec(period)
  if (weekMatch) return weekMatch[1]
  return period
}

const INSUFFICIENT_HISTORY = 'Historique insuffisant pour afficher une évolution.'

export function InsufficientHistoryMessage() {
  return (
    <p className="muted fcc-chart-empty" role="status">
      {INSUFFICIENT_HISTORY}
    </p>
  )
}

export function RevenueExpensesBar({
  points,
  width: widthProp,
}: {
  points: Array<{ period: string; revenue: number; expenses: number }>
  /** Largeur mesurée (ResizeObserver) — sinon 720. */
  width?: number
}) {
  if (points.length === 0) return null
  if (points.length < 2) return <InsufficientHistoryMessage />

  const width = Math.max(280, widthProp ?? 720)
  const height = Math.min(240, Math.round(width * 0.28))
  const max = Math.max(1, ...points.map((p) => Math.max(p.revenue, p.expenses)))
  const slot = width / Math.max(1, points.length)
  const bar = Math.min(16, slot / 3)
  const summary = points
    .map(
      (p) =>
        `${fmtChartPeriod(p.period)} : revenus ${formatEuro(p.revenue)}, dépenses ${formatEuro(p.expenses)}`,
    )
    .join('. ')

  return (
    <div className="fcc-chart">
      <svg
        viewBox={`0 0 ${width} ${height + 28}`}
        style={{ width: '100%', height: 'auto' }}
        role="img"
        aria-label="Revenus versus dépenses"
      >
        {points.map((p, i) => {
          const x = i * slot + slot / 2
          const hr = (p.revenue / max) * height
          const he = (p.expenses / max) * height
          return (
            <g key={p.period}>
              <rect
                x={x - bar - 1}
                y={height - hr}
                width={bar}
                height={hr}
                className="fcc-bar--revenue"
                rx="2"
              >
                <title>{`${fmtChartPeriod(p.period)} — revenus ${formatEuro(p.revenue)}`}</title>
              </rect>
              <rect
                x={x + 1}
                y={height - he}
                width={bar}
                height={he}
                className="fcc-bar--expense"
                rx="2"
              >
                <title>{`${fmtChartPeriod(p.period)} — dépenses ${formatEuro(p.expenses)}`}</title>
              </rect>
              <text
                x={x}
                y={height + 18}
                textAnchor="middle"
                fontSize="10"
                fill="currentColor"
                opacity="0.55"
              >
                {fmtChartPeriod(p.period)}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="fcc-chart-legend" aria-hidden="true">
        <span className="fcc-chart-legend__item fcc-chart-legend__item--revenue">Revenus</span>
        <span className="fcc-chart-legend__item fcc-chart-legend__item--expense">Dépenses</span>
      </div>
      <p className="visually-hidden">{summary}</p>
    </div>
  )
}

export function TreasuryLine({
  points,
  label = 'Évolution trésorerie',
  width: widthProp,
}: {
  points: Array<{ period: string; value: number }>
  label?: string
  width?: number
}) {
  if (points.length === 0) return null
  if (points.length < 2) return <InsufficientHistoryMessage />

  const width = Math.max(240, widthProp ?? 640)
  const height = Math.min(200, Math.round(width * 0.28))
  const values = points.map((p) => p.value)
  const max = Math.max(1, ...values)
  const min = Math.min(0, ...values)
  const range = max - min || 1
  const step = width / Math.max(1, points.length - 1)
  const coords = points.map((p, i) => {
    const x = i * step
    const y = height - ((p.value - min) / range) * height
    return { x, y, p }
  })
  const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ')
  const summary = points
    .map((p) => `${fmtChartPeriod(p.period)} : ${formatEuro(p.value)}`)
    .join('. ')

  return (
    <div className="fcc-chart">
      <svg
        viewBox={`0 0 ${width} ${height + 28}`}
        style={{ width: '100%', height: 'auto' }}
        role="img"
        aria-label={label}
      >
        <path
          d={`${path} L${width},${height} L0,${height} Z`}
          className="fcc-line-fill"
          opacity="0.14"
        />
        <path
          d={path}
          fill="none"
          className="fcc-line-stroke"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />
        {coords.map((c) => (
          <circle key={c.p.period} cx={c.x} cy={c.y} r="3" className="fcc-line-dot">
            <title>{`${fmtChartPeriod(c.p.period)} — ${formatEuro(c.p.value)}`}</title>
          </circle>
        ))}
        {coords
          .filter((_, i) => i % 2 === 0 || i === coords.length - 1)
          .map((c) => (
            <text
              key={`t-${c.p.period}`}
              x={c.x}
              y={height + 18}
              textAnchor="middle"
              fontSize="10"
              fill="currentColor"
              opacity="0.55"
            >
              {fmtChartPeriod(c.p.period)}
            </text>
          ))}
      </svg>
      <p className="visually-hidden">{summary}</p>
    </div>
  )
}

export function HealthScoreGauge({ score, grade }: { score: number; grade: string | null }) {
  const radius = 58
  const circumference = 2 * Math.PI * radius
  const filled = (score / 100) * circumference
  const tone = score >= 65 ? 'ok' : score >= 50 ? 'warn' : 'danger'
  return (
    <svg
      viewBox="0 0 144 144"
      width="136"
      height="136"
      role="img"
      aria-label={`Score ${Math.round(score)}${grade ? ` · ${grade}` : ''}`}
      className={`fcc-gauge fcc-gauge--${tone}`}
    >
      <circle
        cx="72"
        cy="72"
        r={radius}
        fill="none"
        stroke="rgba(148,163,184,0.25)"
        strokeWidth="11"
      />
      <circle
        cx="72"
        cy="72"
        r={radius}
        fill="none"
        className="fcc-gauge__arc"
        strokeWidth="11"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${circumference - filled}`}
        transform="rotate(-90 72 72)"
      />
      <text x="72" y="68" textAnchor="middle" fontSize="30" fontWeight="700" fill="currentColor">
        {Math.round(score)}
      </text>
      {grade ? (
        <text x="72" y="92" textAnchor="middle" fontSize="15" fontWeight="600" className="fcc-gauge__grade">
          {grade}
        </text>
      ) : null}
    </svg>
  )
}

export { INSUFFICIENT_HISTORY }
