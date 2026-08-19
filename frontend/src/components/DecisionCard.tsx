import { Link } from 'react-router-dom'
import {
  actionPathOf,
  actionTypeOf,
  decisionSeverityLabel,
  type DecisionItem,
} from '../decisionCenter'
import { UiBadge } from '../ui/UiStates'

type Props = {
  decision: DecisionItem
  onDismiss?: (id: string) => void
  dismissing?: boolean
  compact?: boolean
}

export default function DecisionCard({ decision, onDismiss, dismissing, compact }: Props) {
  const openAction = decision.available_actions.find((a) => {
    const type = actionTypeOf(a)
    return type !== 'dismiss' && a.enabled && (actionPathOf(a) || a.method === 'NAVIGATE')
  })
  const dismissAction = decision.available_actions.find(
    (a) => actionTypeOf(a) === 'dismiss' && a.enabled,
  )
  const openPath = openAction ? actionPathOf(openAction) : null

  return (
    <article
      className={`panel decision-card severity-${decision.severity}${compact ? ' is-compact' : ''}`}
      aria-labelledby={`decision-title-${decision.id}`}
    >
      <div className="decision-card-head">
        <UiBadge
          tone={
            decision.severity === 'critical' || decision.severity === 'high'
              ? 'warn'
              : decision.severity === 'info'
                ? 'neutral'
                : 'neutral'
          }
        >
          {decisionSeverityLabel(decision.severity)}
        </UiBadge>
        <h3 id={`decision-title-${decision.id}`}>
          <Link to={`/decisions/${decision.id}`}>{decision.title}</Link>
        </h3>
      </div>
      <p className="decision-card-summary">{decision.summary}</p>
      {!compact && decision.explanation ? (
        <p className="muted decision-card-explanation">{decision.explanation}</p>
      ) : null}
      <div className="decision-card-actions actions">
        <Link className="btn secondary" to={`/decisions/${decision.id}`}>
          Détail
        </Link>
        {openPath ? (
          <Link className="btn" to={openPath}>
            {openAction?.label || 'Ouvrir'}
          </Link>
        ) : null}
        {dismissAction && onDismiss ? (
          <button
            type="button"
            className="btn secondary"
            disabled={dismissing}
            aria-busy={dismissing}
            onClick={() => onDismiss(decision.id)}
          >
            {dismissing ? '…' : dismissAction.label}
          </button>
        ) : null}
      </div>
    </article>
  )
}
