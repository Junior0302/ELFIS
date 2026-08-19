type Card = { label: string; value: number | string }

export default function ProcessingSummaryCards({ cards }: { cards: Card[] }) {
  return (
    <div className="processing-summary">
      {cards.map((c) => (
        <div key={c.label} className="processing-summary__card">
          <span className="muted">{c.label}</span>
          <strong>{c.value}</strong>
        </div>
      ))}
    </div>
  )
}
