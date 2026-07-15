type Props = {
  score: number | null | undefined
}

export default function ConfidenceMeter({ score }: Props) {
  const value = Math.max(0, Math.min(1, score ?? 0))
  const pct = Math.round(value * 100)
  const tone = value >= 0.85 ? 'good' : value >= 0.7 ? 'mid' : 'low'

  return (
    <div className={`confidence confidence-${tone}`}>
      <div className="confidence-top">
        <span>Score de confiance</span>
        <strong>{pct}%</strong>
      </div>
      <div className="confidence-track">
        <div className="confidence-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
