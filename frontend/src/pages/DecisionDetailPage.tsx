import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import DecisionActionPanel from '../components/DecisionActionPanel'
import DecisionEvidenceList from '../components/DecisionEvidenceList'
import DecisionExecutionStatusBadge from '../components/DecisionExecutionStatus'
import DecisionHistory from '../components/DecisionHistory'
import DecisionResolutionPanel from '../components/DecisionResolutionPanel'
import {
  actionPathOf,
  actionTypeOf,
  decisionSeverityLabel,
  decisionStatusLabel,
  markDecisionsStale,
  type DecisionAction,
  type DecisionDetail,
} from '../decisionCenter'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../ui/UiStates'

function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  busy,
  onCancel,
  onConfirm,
  children,
}: {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  busy?: boolean
  onCancel: () => void
  onConfirm: () => void
  children?: ReactNode
}) {
  const titleId = useId()
  if (!open) return null
  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-panel panel decision-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id={titleId}>{title}</h3>
        <p>{description}</p>
        {children}
        <div className="actions">
          <button type="button" className="btn secondary" onClick={onCancel} disabled={busy}>
            Annuler
          </button>
          <button type="button" className="btn" onClick={onConfirm} disabled={busy} aria-busy={busy}>
            {busy ? '…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function DecisionDetailPage() {
  const { decisionId } = useParams<{ decisionId: string }>()
  const { token, orgId } = useAuth()
  const liveRef = useRef<HTMLParagraphElement>(null)
  const [decision, setDecision] = useState<DecisionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('')
  const [busyAction, setBusyAction] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<DecisionAction | null>(null)
  const [confirmBalanced, setConfirmBalanced] = useState(false)
  const [confirmReviewed, setConfirmReviewed] = useState(false)

  const load = () => {
    if (!token || orgId == null || !decisionId) return
    setLoading(true)
    setError('')
    void api
      .getDecision(decisionId, token, orgId)
      .then((res) => setDecision(res))
      .catch((e) => setError(e instanceof Error ? e.message : 'Impossible de charger la décision'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [token, orgId, decisionId])

  useEffect(() => {
    if (statusMessage && liveRef.current) {
      liveRef.current.focus()
    }
  }, [statusMessage, error])

  const refreshAfterMutation = (next: DecisionDetail, message: string) => {
    setDecision(next)
    setStatusMessage(message)
    markDecisionsStale()
  }

  const runAction = async (action: DecisionAction) => {
    if (!token || orgId == null || !decisionId) return
    const type = actionTypeOf(action)
    setBusyAction(type)
    setError('')
    setStatusMessage('')
    try {
      if (type === 'dismiss') {
        await api.dismissDecision(decisionId, token, orgId)
        const detail = await api.getDecision(decisionId, token, orgId, { sync: false })
        refreshAfterMutation(detail, 'Décision ignorée.')
        return
      }
      const body =
        type === 'validate_accounting_proposal'
          ? {
              confirm_balanced_entry: confirmBalanced,
              confirm_document_reviewed: confirmReviewed,
              idempotency_key: `${decisionId}:${type}:${Date.now()}`,
            }
          : { idempotency_key: `${decisionId}:${type}:${Date.now()}` }
      const res = await api.executeDecisionAction(decisionId, type, token, orgId, body)
      refreshAfterMutation(
        res.decision,
        res.result.message ||
          (res.decision.status === 'resolved'
            ? 'Décision résolue.'
            : 'Action effectuée. La cause est réévaluée.'),
      )
      if (res.result.navigation_path && res.decision.status !== 'resolved') {
        // Navigation optionnelle laissée à l’utilisateur via les actions
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'L’action a échoué')
    } finally {
      setBusyAction(null)
      setPendingAction(null)
      setConfirmBalanced(false)
      setConfirmReviewed(false)
    }
  }

  const onExecute = (action: DecisionAction) => {
    if (action.requires_confirmation) {
      setPendingAction(action)
      return
    }
    void runAction(action)
  }

  if (loading && !decision) {
    return (
      <div aria-busy="true" aria-live="polite">
        <Skeleton rows={6} />
      </div>
    )
  }

  if (error && !decision) {
    return <ErrorState message={error} onRetry={load} />
  }

  if (!decision) {
    return (
      <EmptyState
        title="Décision introuvable"
        description="Cette décision n’existe pas ou n’est plus accessible."
      />
    )
  }

  const primaryNav = decision.available_actions.find(
    (a) => (a.method || 'NAVIGATE') === 'NAVIGATE' && a.enabled && actionPathOf(a),
  )

  return (
    <>
      <div className="page-head">
        <div>
          <p className="muted first-experience-back">
            <Link to="/decisions">Retour aux décisions</Link>
          </p>
          <h2 id="decision-detail-title">{decision.title}</h2>
          <p>{decision.summary}</p>
        </div>
      </div>

      {statusMessage ? (
        <p className="panel form-ok" role="status" aria-live="polite" tabIndex={-1} ref={liveRef}>
          {statusMessage}
        </p>
      ) : null}
      {error ? (
        <p className="panel form-error" role="alert" tabIndex={-1} ref={liveRef}>
          {error}
        </p>
      ) : null}

      {decision.status === 'resolved' ? (
        <DecisionResolutionPanel
          resolvedAt={decision.resolved_at}
          lastAction={decision.last_action_type}
          sourcePath={actionPathOf(primaryNav || decision.available_actions[0] || { type: '', label: '', enabled: false }) || decision.recommended_action_path || undefined}
        />
      ) : null}

      <div className="decision-detail-layout">
        <section className="panel" aria-labelledby="decision-detail-main">
          <h3 id="decision-detail-main">Comprendre</h3>
          <div className="decision-card-head">
            <UiBadge tone={decision.severity === 'high' || decision.severity === 'critical' ? 'warn' : 'neutral'}>
              {decisionSeverityLabel(decision.severity)}
            </UiBadge>
            <UiBadge tone="neutral">{decisionStatusLabel(decision.status)}</UiBadge>
          </div>
          <DecisionExecutionStatusBadge
            status={decision.execution_status}
            errorMessage={decision.last_execution_error_message}
          />
          <p>{decision.explanation}</p>
          <dl className="decision-qa">
            <div>
              <dt>Qu’est-ce qui a été détecté ?</dt>
              <dd>{decision.what_was_detected || decision.summary}</dd>
            </div>
            <div>
              <dt>Pourquoi est-ce important ?</dt>
              <dd>{decision.why_it_matters}</dd>
            </div>
            <div>
              <dt>Sur quelle donnée ?</dt>
              <dd>
                {decision.source_label || decision.source_type} · {decision.source_id}
              </dd>
            </div>
            <div>
              <dt>Que dois-je faire ?</dt>
              <dd>{decision.what_to_do}</dd>
            </div>
            <div>
              <dt>Après l’action ?</dt>
              <dd>{decision.what_happens_after}</dd>
            </div>
          </dl>
          <h4>Preuves</h4>
          <DecisionEvidenceList evidence={decision.evidence || []} />
        </section>

        <aside className="decision-detail-aside">
          <section className="panel" aria-labelledby="decision-actions-title">
            <h3 id="decision-actions-title">Actions</h3>
            <DecisionActionPanel
              decision={decision}
              busyAction={busyAction}
              onExecute={onExecute}
              onDismiss={() => {
                const dismiss = decision.available_actions.find((a) => actionTypeOf(a) === 'dismiss')
                if (dismiss?.requires_confirmation) setPendingAction(dismiss)
                else void runAction(dismiss || { type: 'dismiss', label: 'Ignorer', enabled: true })
              }}
            />
          </section>
          <section className="panel" aria-labelledby="decision-history-title">
            <h3 id="decision-history-title">Historique</h3>
            <DecisionHistory items={decision.history || []} />
            <p className="muted">
              Créée le{' '}
              {new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(
                new Date(decision.created_at),
              )}
              {' · '}
              Mise à jour le{' '}
              {new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(
                new Date(decision.updated_at),
              )}
            </p>
          </section>
        </aside>
      </div>

      <ConfirmDialog
        open={Boolean(pendingAction)}
        title={pendingAction?.label || 'Confirmer'}
        description={
          pendingAction?.description ||
          'Confirmez cette action. Elle sera exécutée via le module métier existant.'
        }
        confirmLabel={pendingAction?.label || 'Confirmer'}
        busy={Boolean(busyAction)}
        onCancel={() => setPendingAction(null)}
        onConfirm={() => {
          if (!pendingAction) return
          if (actionTypeOf(pendingAction) === 'validate_accounting_proposal') {
            if (!confirmBalanced || !confirmReviewed) {
              setError('Confirmez l’écriture équilibrée et la revue du document avant de valider.')
              return
            }
          }
          void runAction(pendingAction)
        }}
      >
        {pendingAction && actionTypeOf(pendingAction) === 'validate_accounting_proposal' ? (
          <form
            className="decision-confirm-form"
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
            }}
          >
            <label>
              <input
                type="checkbox"
                checked={confirmBalanced}
                onChange={(e) => setConfirmBalanced(e.target.checked)}
              />{' '}
              Je confirme que l’écriture est équilibrée
            </label>
            <label>
              <input
                type="checkbox"
                checked={confirmReviewed}
                onChange={(e) => setConfirmReviewed(e.target.checked)}
              />{' '}
              J’ai examiné le document source
            </label>
            <p className="muted">Cette validation n’est pas automatique : elle respecte les règles Accounting.</p>
          </form>
        ) : null}
        {pendingAction && actionTypeOf(pendingAction) === 'dismiss' ? (
          <p className="muted">Ignorer masque la décision sans corriger la cause métier.</p>
        ) : null}
      </ConfirmDialog>
    </>
  )
}
