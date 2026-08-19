/** Visualisations légères SVG — données déjà agrégées côté API uniquement. */

type BarProps = {
  items: Array<{ label: string; value: number }>
  title?: string
}

export function PlatformBarChart({ items, title }: BarProps) {
  const max = Math.max(1, ...items.map((i) => i.value))
  if (!items.length) {
    return (
      <div className="pc-chart pc-chart-empty">
        <p>Donnée indisponible</p>
      </div>
    )
  }
  return (
    <figure className="pc-chart pc-chart-bars" aria-label={title || 'Graphique en barres'}>
      {title && <figcaption>{title}</figcaption>}
      <ul>
        {items.map((item) => (
          <li key={item.label}>
            <span className="pc-chart-label">{item.label}</span>
            <span className="pc-chart-track">
              <span
                className="pc-chart-fill"
                style={{ width: `${Math.round((item.value / max) * 100)}%` }}
              />
            </span>
            <strong className="pc-chart-val">{item.value}</strong>
          </li>
        ))}
      </ul>
    </figure>
  )
}

type DonutProps = {
  parts: Array<{ label: string; value: number; tone?: string }>
  title?: string
}

export function PlatformDonut({ parts, title }: DonutProps) {
  const total = parts.reduce((s, p) => s + Math.max(0, p.value), 0)
  if (!parts.length || total <= 0) {
    return (
      <div className="pc-chart pc-chart-empty">
        <p>Donnée indisponible</p>
      </div>
    )
  }
  const r = 36
  const c = 2 * Math.PI * r
  let offset = 0
  const colors = ['#3ecf8e', '#f0b429', '#f04438', '#7aa2ff', '#a78bfa', '#94a3b8']
  return (
    <figure className="pc-chart pc-chart-donut" aria-label={title || 'Répartition'}>
      {title && <figcaption>{title}</figcaption>}
      <div className="pc-donut-wrap">
        <svg viewBox="0 0 100 100" width="112" height="112" role="img">
          <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="12" />
          {parts.map((p, i) => {
            const len = (Math.max(0, p.value) / total) * c
            const el = (
              <circle
                key={p.label}
                cx="50"
                cy="50"
                r={r}
                fill="none"
                stroke={colors[i % colors.length]}
                strokeWidth="12"
                strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-offset}
                transform="rotate(-90 50 50)"
              />
            )
            offset += len
            return el
          })}
          <text x="50" y="52" textAnchor="middle" className="pc-donut-center">
            {total}
          </text>
        </svg>
        <ul className="pc-donut-legend">
          {parts.map((p, i) => (
            <li key={p.label}>
              <span style={{ background: colors[i % colors.length] }} aria-hidden />
              {p.label}: <strong>{p.value}</strong>
            </li>
          ))}
        </ul>
      </div>
    </figure>
  )
}

type SparkProps = {
  values: number[]
  label?: string
}

/** Sparkline : uniquement si plusieurs points réels sont fournis. */
export function PlatformSparkline({ values, label }: SparkProps) {
  if (values.length < 2) {
    return (
      <div className="pc-spark pc-chart-empty" title={label}>
        <span>Donnée indisponible</span>
      </div>
    )
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(1, max - min)
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100
      const y = 28 - ((v - min) / span) * 24
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg
      className="pc-spark"
      viewBox="0 0 100 32"
      width="100%"
      height="32"
      aria-label={label || 'Tendance'}
    >
      <polyline fill="none" stroke="#3ecf8e" strokeWidth="2" points={points} />
    </svg>
  )
}
