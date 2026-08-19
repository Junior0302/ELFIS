import { Link } from 'react-router-dom'
import {
  formatCommandMetric,
  healthStatusLabel,
  severityLabel,
  type CommandCenterData,
} from '../commandCenter'
import { decisionSeverityLabel } from '../decisionCenter'
import { withLaunchSource } from '../firstExperience'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../ui/UiStates'

type Props = {
  data: CommandCenterData | null
  loading: boolean
  error: string
  onRetry: () => void
  /** Lorsque le démarrage Launch est terminé, le Command Center est mis en avant. */
  emphasize?: boolean
}

function PriorityCenter({ data }: { data: CommandCenterData }) {
  if (data.priorities.length === 0) {
    return (
      <section className="panel command-block" aria-labelledby="cc-priorities-title">
        <h3 id="cc-priorities-title">Priorités</h3>
        <EmptyState
          title="Rien d’urgent pour le moment"
          description="Les prochaines actions importantes apparaîtront ici."
        />
      </section>
    )
  }

  return (
    <section className="panel command-block" aria-labelledby="cc-priorities-title">
      <h3 id="cc-priorities-title">Que dois-je faire maintenant ?</h3>
      <ul className="command-priority-list">
        {data.priorities.map((p) => (
          <li key={p.id} className={`command-priority-item severity-${p.severity}`}>
            <div className="command-priority-copy">
              <UiBadge tone={p.severity === 'critical' || p.severity === 'high' ? 'warn' : 'neutral'}>
                {severityLabel(p.severity)}
              </UiBadge>
              <strong>{p.title}</strong>
              <p className="muted">{p.description}</p>
            </div>
            <Link className="btn secondary" to={p.action_path}>
              Ouvrir
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

function SmartSummary({ data }: { data: CommandCenterData }) {
  return (
    <section className="panel command-block" aria-labelledby="cc-summary-title">
      <h3 id="cc-summary-title">Résumé</h3>
      <p className="command-summary-headline">{data.smart_summary.headline}</p>
      {data.smart_summary.metrics.length === 0 ? (
        <EmptyState title="Aucun indicateur disponible" description="Les compteurs réels apparaîtront dès que des données existent." />
      ) : (
        <ul className="command-summary-metrics">
          {data.smart_summary.metrics.map((m) => (
            <li key={m.key}>
              {m.path ? (
                <Link to={m.path} className="command-summary-metric">
                  <span className="muted">{m.label}</span>
                  <strong>{formatCommandMetric(m)}</strong>
                </Link>
              ) : (
                <div className="command-summary-metric">
                  <span className="muted">{m.label}</span>
                  <strong>{formatCommandMetric(m)}</strong>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function ActivityTimeline({ data }: { data: CommandCenterData }) {
  return (
    <section className="panel command-block" aria-labelledby="cc-timeline-title">
      <h3 id="cc-timeline-title">Activité récente</h3>
      {data.activity_timeline.length === 0 ? (
        <EmptyState
          title="Aucune activité pour le moment"
          description="Clients, factures et documents apparaîtront ici."
        />
      ) : (
        <ol className="command-timeline">
          {data.activity_timeline.map((item) => (
            <li key={item.id}>
              {item.path ? (
                <Link to={item.path} className="command-timeline-item">
                  <strong>{item.title}</strong>
                  <span>{item.description}</span>
                </Link>
              ) : (
                <div className="command-timeline-item">
                  <strong>{item.title}</strong>
                  <span>{item.description}</span>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function AIInsightsCard({ data }: { data: CommandCenterData }) {
  const block = data.ai_insights
  const wqPath = block.work_queue_path || '/work-queue'
  const counts = block.counts
  return (
    <section className="panel command-block" aria-labelledby="cc-ai-title">
      <div className="command-block-head" style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'baseline' }}>
        <h3 id="cc-ai-title">{block.title || 'À examiner'}</h3>
        <Link className="linkish" to={wqPath}>
          Boîte de travail
        </Link>
      </div>
      {counts ? (
        <p className="muted" role="status">
          {counts.todo} à traiter · {counts.in_progress} en cours · {counts.waiting} en attente
        </p>
      ) : null}
      {block.status === 'empty' || block.insights.length === 0 ? (
        <p className="muted" role="status">
          {block.message || 'Aucune décision ne nécessite votre attention actuellement.'}
        </p>
      ) : (
        <ul className="command-decision-insights">
          {block.insights.slice(0, 3).map((insight) => (
            <li key={insight.decision_id} className="command-decision-insight">
              <div>
                <UiBadge
                  tone={
                    insight.severity === 'critical' || insight.severity === 'high' ? 'warn' : 'neutral'
                  }
                >
                  {decisionSeverityLabel(insight.severity)}
                </UiBadge>
                <strong>{insight.title}</strong>
                <p className="muted">{insight.summary}</p>
              </div>
              {insight.action_path ? (
                <Link className="btn secondary" to={insight.action_path}>
                  {insight.action_label}
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function SystemHealthCard({ data }: { data: CommandCenterData }) {
  return (
    <section className="panel command-block" aria-labelledby="cc-health-title">
      <h3 id="cc-health-title">Santé du système</h3>
      {data.system_health.services.length === 0 ? (
        <EmptyState
          title="Aucun état connu"
          description="Les services ne s’affichent que lorsque leur état est réellement vérifié."
        />
      ) : (
        <ul className="command-health-list">
          {data.system_health.services.map((s) => (
            <li key={s.key} className="command-health-item">
              <div>
                <strong>{s.label}</strong>
                {s.detail ? <p className="muted">{s.detail}</p> : null}
              </div>
              <UiBadge
                tone={
                  s.status === 'ok' ? 'ok' : s.status === 'warning' || s.status === 'degraded' ? 'warn' : 'danger'
                }
              >
                {healthStatusLabel(s.status)}
              </UiBadge>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function QuickActionsBlock({ data }: { data: CommandCenterData }) {
  if (data.quick_actions.length === 0) return null
  return (
    <section className="panel command-block" aria-labelledby="cc-quick-title">
      <h3 id="cc-quick-title">Actions rapides</h3>
      <ul className="command-quick-actions">
        {data.quick_actions.map((action) => (
          <li key={action.key}>
            <Link to={withLaunchSource(action.path)} className="command-quick-action">
              <strong>{action.label}</strong>
              <span className="muted">{action.description}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function CommandCenter({ data, loading, error, onRetry, emphasize = false }: Props) {
  if (loading && !data) {
    return (
      <section className="panel command-center" aria-busy="true" aria-live="polite">
        <Skeleton rows={6} />
      </section>
    )
  }

  if (error && !data) {
    return (
      <section className="panel command-center">
        <ErrorState message={error} onRetry={onRetry} />
      </section>
    )
  }

  if (!data) return null

  return (
    <section
      className={`command-center${emphasize ? ' is-emphasized' : ''}`}
      aria-labelledby="command-center-title"
    >
      <header className="command-center-header">
        <div>
          <p className="launch-dashboard-eyebrow">Command Center</p>
          <h2 id="command-center-title">Centre de commande</h2>
          <p className="muted">
            Point d’entrée quotidien pour {data.organization_name || 'votre organisation'}.
          </p>
        </div>
        {error ? (
          <p className="form-error" role="alert">
            {error}{' '}
            <button type="button" className="linkish" onClick={onRetry}>
              Réessayer
            </button>
          </p>
        ) : null}
      </header>

      <div className="command-center-grid">
        <div className="command-center-main">
          <PriorityCenter data={data} />
          <SmartSummary data={data} />
          <ActivityTimeline data={data} />
        </div>
        <aside className="command-center-side">
          <QuickActionsBlock data={data} />
          <AIInsightsCard data={data} />
          <SystemHealthCard data={data} />
        </aside>
      </div>
    </section>
  )
}

export {
  PriorityCenter,
  SmartSummary,
  ActivityTimeline,
  AIInsightsCard,
  SystemHealthCard,
}
