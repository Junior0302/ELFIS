import { Link } from 'react-router-dom'
import {
  actionPathOf,
  actionTypeOf,
  type DecisionAction,
  type DecisionItem,
} from '../decisionCenter'

type Props = {
  decision: DecisionItem
  busyAction?: string | null
  onExecute: (action: DecisionAction) => void
  onDismiss?: () => void
}

export default function DecisionActionPanel({ decision, busyAction, onExecute, onDismiss }: Props) {
  const actions = decision.available_actions || []
  if (!actions.length) {
    return <p className="muted">Aucune action disponible pour cette décision.</p>
  }

  return (
    <div className="decision-action-panel" aria-label="Actions disponibles">
      <ul className="decision-action-list">
        {actions.map((action) => {
          const type = actionTypeOf(action)
          const path = actionPathOf(action)
          const busy = busyAction === type
          const method = action.method || (type === 'dismiss' ? 'POST' : 'NAVIGATE')

          if (!action.enabled) {
            return (
              <li key={type} className="decision-action-item is-disabled">
                <button type="button" className="btn secondary" disabled aria-disabled="true">
                  {action.label}
                </button>
                {action.disabled_reason ? (
                  <p className="muted" id={`action-reason-${type}`}>
                    {action.disabled_reason}
                  </p>
                ) : null}
              </li>
            )
          }

          if (method === 'NAVIGATE' && path) {
            return (
              <li key={type} className="decision-action-item">
                <Link className="btn" to={path}>
                  {action.label}
                </Link>
                {action.description ? <p className="muted">{action.description}</p> : null}
              </li>
            )
          }

          if (type === 'dismiss' && onDismiss) {
            return (
              <li key={type} className="decision-action-item">
                <button
                  type="button"
                  className="btn secondary"
                  disabled={busy}
                  aria-busy={busy}
                  onClick={onDismiss}
                >
                  {busy ? '…' : action.label}
                </button>
                {action.description ? <p className="muted">{action.description}</p> : null}
              </li>
            )
          }

          return (
            <li key={type} className="decision-action-item">
              <button
                type="button"
                className="btn"
                disabled={busy}
                aria-busy={busy}
                onClick={() => onExecute(action)}
              >
                {busy ? 'Action en cours…' : action.label}
              </button>
              {action.description ? <p className="muted">{action.description}</p> : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
