import type { DecisionHistoryItem } from '../decisionCenter'

type Props = {
  items: DecisionHistoryItem[]
}

function formatAt(value: string): string {
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value))
  } catch {
    return value
  }
}

export default function DecisionHistory({ items }: Props) {
  if (!items.length) {
    return <p className="muted">Aucun historique pour le moment.</p>
  }
  return (
    <ol className="decision-history" aria-label="Historique de la décision">
      {items.map((item) => (
        <li key={item.id}>
          <strong>{item.label}</strong>
          <span className="muted">{formatAt(item.at)}</span>
          {item.action_type ? <span className="muted"> · {item.action_type}</span> : null}
          {item.error_message ? <p className="form-error">{item.error_message}</p> : null}
        </li>
      ))}
    </ol>
  )
}
