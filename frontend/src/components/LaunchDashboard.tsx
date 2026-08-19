import { Link, useNavigate } from 'react-router-dom'
import {
  Badge,
  Button,
  EmptyState,
  Progress,
  QuickActionCard,
} from '../design-system'
import { ErrorState, Skeleton } from '../ui/UiStates'
import { withLaunchSource } from '../firstExperience'
import {
  launchWelcomeLead,
  launchWelcomeTitle,
  type LaunchDashboardData,
} from '../launchDashboard'

type Props = {
  data: LaunchDashboardData | null
  loading: boolean
  error: string
  onRetry: () => void
  collapsed: boolean
  onToggleCollapsed: () => void
}

export default function LaunchDashboard({
  data,
  loading,
  error,
  onRetry,
  collapsed,
  onToggleCollapsed,
}: Props) {
  const navigate = useNavigate()

  if (loading && !data) {
    return (
      <section className="panel launch-dashboard" aria-busy="true" aria-live="polite">
        <Skeleton rows={5} />
      </section>
    )
  }

  if (error && !data) {
    return (
      <section className="panel launch-dashboard">
        <ErrorState message={error} onRetry={onRetry} />
      </section>
    )
  }

  if (!data) return null

  const { onboarding, organization, user, quick_actions, recent_activity, workspace_ready } =
    data
  const allDone = onboarding.all_completed

  return (
    <section className="panel launch-dashboard" aria-labelledby="launch-dashboard-title">
      <header className="launch-dashboard-header">
        <div>
          <p className="launch-dashboard-eyebrow">Démarrage</p>
          <h2 id="launch-dashboard-title">{launchWelcomeTitle(user.display_name)}</h2>
          <p className="launch-dashboard-lead">
            {launchWelcomeLead(organization.name, workspace_ready)}
          </p>
        </div>
        {allDone ? (
          <button type="button" className="linkish" onClick={onToggleCollapsed}>
            {collapsed ? 'Afficher le démarrage' : 'Réduire'}
          </button>
        ) : null}
      </header>

      {error ? (
        <p className="form-error" role="alert">
          {error}{' '}
          <button type="button" className="linkish" onClick={onRetry}>
            Réessayer
          </button>
        </p>
      ) : null}

      {collapsed && allDone ? (
        <p className="muted launch-dashboard-done">Démarrage terminé — checklist masquée.</p>
      ) : (
        <div className="launch-dashboard-grid">
          <div className="launch-dashboard-main">
            <div className="launch-progress-card">
              <p className="launch-progress-label">
                {onboarding.completed_steps} étapes terminées sur {onboarding.total_steps}
              </p>
              <Progress
                value={onboarding.progress}
                label={`Progression du démarrage : ${onboarding.progress} pour cent`}
              />
              {allDone ? (
                <p className="launch-dashboard-done" role="status">
                  Démarrage terminé. Vous pouvez continuer à utiliser ComptaPilot.
                </p>
              ) : null}
            </div>

            <ul className="launch-checklist" aria-label="Checklist de démarrage">
              {onboarding.steps.map((step) => (
                <li
                  key={step.key}
                  className={`launch-checklist-item${step.completed ? ' is-done' : ''}`}
                >
                  <div className="launch-checklist-copy">
                    <Badge tone={step.completed ? 'ok' : 'neutral'}>
                      {step.completed ? 'Terminée' : 'À faire'}
                    </Badge>
                    <span className="launch-checklist-label">{step.label}</span>
                  </div>
                  {!step.completed && step.action_path && step.action_label ? (
                    <Link
                      className="btn secondary launch-checklist-action"
                      to={withLaunchSource(step.action_path)}
                    >
                      {step.action_label}
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>

          <aside className="launch-dashboard-side">
            {onboarding.recommended_action ? (
              <div className="launch-recommended">
                <p className="launch-dashboard-eyebrow">Action recommandée</p>
                <h3>{onboarding.recommended_action.title}</h3>
                <p>{onboarding.recommended_action.description}</p>
                <Button
                  type="button"
                  onClick={() =>
                    navigate(withLaunchSource(onboarding.recommended_action!.action_path))
                  }
                >
                  {onboarding.recommended_action.action_label}
                </Button>
              </div>
            ) : null}

            {quick_actions.length > 0 ? (
              <div className="launch-quick-actions">
                <h3>Actions rapides</h3>
                <ul>
                  {quick_actions.map((action) => (
                    <li key={action.key}>
                      <QuickActionCard
                        title={action.label}
                        description={action.description}
                        href={withLaunchSource(action.path)}
                        accent
                      />
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="launch-recent">
              <h3>Activité récente</h3>
              {recent_activity.length === 0 ? (
                <EmptyState
                  title="Aucune activité pour le moment"
                  description="Vos clients, factures et documents apparaîtront ici."
                />
              ) : (
                <ul className="launch-recent-list">
                  {recent_activity.map((item) => (
                    <li key={item.id}>
                      {item.path ? (
                        <Link to={item.path} className="launch-recent-item">
                          <strong>{item.title}</strong>
                          <span>{item.description}</span>
                        </Link>
                      ) : (
                        <div className="launch-recent-item">
                          <strong>{item.title}</strong>
                          <span>{item.description}</span>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      )}
    </section>
  )
}

