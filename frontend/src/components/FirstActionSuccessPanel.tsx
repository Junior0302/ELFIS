import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { FirstExperienceAction } from '../firstExperience'

type Props = {
  title: string
  description: string
  resourceName?: string | null
  primaryAction: FirstExperienceAction
  secondaryActions?: FirstExperienceAction[]
  extra?: ReactNode
  className?: string
}

function ActionControl({ action }: { action: FirstExperienceAction }) {
  const className = action.tone === 'secondary' ? 'btn secondary' : 'btn'
  if (action.to) {
    return (
      <Link className={className} to={action.to}>
        {action.label}
      </Link>
    )
  }
  return (
    <button type="button" className={className} onClick={action.onClick}>
      {action.label}
    </button>
  )
}

export default function FirstActionSuccessPanel({
  title,
  description,
  resourceName,
  primaryAction,
  secondaryActions = [],
  extra,
  className = '',
}: Props) {
  return (
    <section
      className={`panel first-action-success ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-labelledby="first-action-success-title"
    >
      <div className="first-action-success-icon" aria-hidden="true">
        ✓
      </div>
      <div className="first-action-success-copy">
        <h3 id="first-action-success-title">{title}</h3>
        <p>
          {description}
          {resourceName ? (
            <>
              {' '}
              <strong>{resourceName}</strong>
            </>
          ) : null}
        </p>
        {extra}
        <div className="first-action-success-actions actions">
          <ActionControl action={primaryAction} />
          {secondaryActions.map((action) => (
            <ActionControl key={`${action.label}-${action.to || 'btn'}`} action={action} />
          ))}
        </div>
      </div>
    </section>
  )
}
