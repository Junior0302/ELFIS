import { useEffect, useId, useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, type WorkspaceProvisionStatus } from '../api'
import { useAuth } from '../auth'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import {
  clearEnterpriseSetupDraftFromStorage,
  firstIncompleteEnterpriseSetupPath,
  isEnterpriseSetupDraftComplete,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'
import {
  PROVISION_UI_STEPS,
  provisionStepLabel,
  resolveProvisionUiStepState,
} from '../workspaceProvisioning'

const DASHBOARD_PATH = '/dashboard'

/** Anti double-démarrage (React Strict Mode / remount). */
const provisionStartLocks = new Set<string>()

/**
 * Étape 7 — provisioning réel (POST/GET /api/workspace/provision).
 * Ne démarre qu’une seule fois (garde Strict Mode).
 */
export default function EnterpriseSetupPreparationPlaceholderPage() {
  const titleId = useId()
  const liveId = useId()
  const navigate = useNavigate()
  const { token, orgId } = useAuth()
  const { draft } = useEnterpriseSetupDraft()

  const incompletePath = firstIncompleteEnterpriseSetupPath(draft)
  const [status, setStatus] = useState<WorkspaceProvisionStatus | null>(null)
  const [bootError, setBootError] = useState('')
  const startedRef = useRef(false)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    if (incompletePath) return
    if (!token || orgId == null) {
      setBootError('Session invalide. Reconnectez-vous.')
      return
    }
    const lockKey = `provision:${orgId}`
    if (startedRef.current || provisionStartLocks.has(lockKey)) return
    startedRef.current = true
    provisionStartLocks.add(lockKey)

    let cancelled = false

    const apply = (next: WorkspaceProvisionStatus) => {
      if (cancelled) return
      setStatus(next)
      if (next.status === 'completed' && next.setup_completed) {
        clearEnterpriseSetupDraftFromStorage()
        provisionStartLocks.delete(lockKey)
      }
      if (next.status === 'failed') {
        provisionStartLocks.delete(lockKey)
      }
    }

    const startOrResume = async () => {
      try {
        const current = await api.getWorkspaceProvisionStatus(token, orgId)
        if (cancelled) return
        if (current.status === 'completed' || current.setup_completed) {
          apply(current)
          return
        }
        if (current.status === 'running') {
          apply(current)
          return
        }
        if (current.status === 'failed') {
          apply(current)
          return
        }
        if (!isEnterpriseSetupDraftComplete(draft)) {
          provisionStartLocks.delete(lockKey)
          return
        }
        const created = await api.provisionWorkspace(token, orgId, {
          company_name: draft.company_name,
          industry: draft.industry,
          industry_other: draft.industry_other ?? null,
          country: draft.country,
          currency: draft.currency,
          vat_status: draft.vat_status,
          vat_number: draft.vat_number ?? null,
        })
        apply(created)
      } catch (reason) {
        provisionStartLocks.delete(lockKey)
        if (cancelled) return
        setBootError(
          reason instanceof Error
            ? reason.message
            : 'Impossible de préparer votre espace. Réessayez.',
        )
        startedRef.current = false
      }
    }

    void startOrResume()
    return () => {
      cancelled = true
      if (pollRef.current != null) {
        window.clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [token, orgId, draft, incompletePath])

  useEffect(() => {
    if (!token || orgId == null) return
    if (status?.status !== 'running') {
      if (pollRef.current != null) {
        window.clearInterval(pollRef.current)
        pollRef.current = null
      }
      return
    }
    pollRef.current = window.setInterval(() => {
      void api
        .getWorkspaceProvisionStatus(token, orgId)
        .then((next) => {
          setStatus(next)
          if (next.status === 'completed' && next.setup_completed) {
            clearEnterpriseSetupDraftFromStorage()
          }
        })
        .catch(() => undefined)
    }, 1500)
    return () => {
      if (pollRef.current != null) {
        window.clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [status?.status, token, orgId])

  const onRetry = async () => {
    if (!token || orgId == null || !isEnterpriseSetupDraftComplete(draft)) return
    const lockKey = `provision:${orgId}`
    setBootError('')
    startedRef.current = true
    provisionStartLocks.add(lockKey)
    try {
      const next = await api.provisionWorkspace(token, orgId, {
        company_name: draft.company_name,
        industry: draft.industry,
        industry_other: draft.industry_other ?? null,
        country: draft.country,
        currency: draft.currency,
        vat_status: draft.vat_status,
        vat_number: draft.vat_number ?? null,
      })
      setStatus(next)
      if (next.status === 'completed') {
        clearEnterpriseSetupDraftFromStorage()
        provisionStartLocks.delete(lockKey)
      }
      if (next.status === 'failed') provisionStartLocks.delete(lockKey)
    } catch (reason) {
      provisionStartLocks.delete(lockKey)
      setBootError(
        reason instanceof Error
          ? reason.message
          : 'Impossible de préparer votre espace. Réessayez.',
      )
      startedRef.current = false
    }
  }

  if (incompletePath) {
    return <Navigate to={incompletePath} replace />
  }

  const progress = status?.progress ?? 0
  const currentStep = status?.current_step ?? 'pending'
  const provisionStatus = status?.status ?? 'pending'
  const completed = provisionStatus === 'completed' || Boolean(status?.setup_completed)
  const failed = provisionStatus === 'failed'

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={titleId}>
      <EnterpriseSetupProgress stepId="preparation" />
      {completed ? (
        <>
          <h2 id={titleId}>Votre espace est prêt</h2>
          <p className="enterprise-setup-lead">
            La configuration initiale de votre entreprise est terminée.
          </p>
          <div className="enterprise-setup-actions">
            <button className="btn" type="button" onClick={() => navigate(DASHBOARD_PATH)}>
              Accéder à ComptaPilot
            </button>
          </div>
        </>
      ) : (
        <>
          <h2 id={titleId}>Préparation de votre espace</h2>
          <p className="enterprise-setup-lead">
            Nous configurons ComptaPilot à partir des informations de votre entreprise.
          </p>

          <div
            className="enterprise-setup-provision-progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
            aria-label={`Progression : ${progress} pour cent`}
          >
            <div
              className="enterprise-setup-provision-progress-bar"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>

          <p id={liveId} className="visually-hidden" aria-live="polite">
            {failed
              ? status?.error_message || 'Une erreur est survenue.'
              : `Étape en cours : ${currentStep}. Progression ${progress} %.`}
          </p>

          <ol className="enterprise-setup-provision-steps">
            {PROVISION_UI_STEPS.map((step) => {
              const state = resolveProvisionUiStepState(
                step.id,
                currentStep,
                provisionStatus,
              )
              return (
                <li
                  key={step.id}
                  className={`enterprise-setup-provision-step is-${state}`}
                  aria-current={state === 'current' ? 'step' : undefined}
                >
                  <span className="enterprise-setup-provision-step-label">{step.label}</span>
                  <span className="enterprise-setup-provision-step-state">
                    {provisionStepLabel(state)}
                  </span>
                </li>
              )
            })}
          </ol>

          {(bootError || failed) && (
            <p className="enterprise-setup-field-error" role="alert">
              {bootError ||
                status?.error_message ||
                'La préparation de votre espace a échoué. Vous pouvez réessayer.'}
            </p>
          )}

          <div className="enterprise-setup-actions">
            {failed || bootError ? (
              <button className="btn" type="button" onClick={() => void onRetry()}>
                Réessayer
              </button>
            ) : null}
            {!failed && !bootError ? (
              <Link className="btn secondary" to="/onboarding/entreprise/resume">
                Retour
              </Link>
            ) : (
              <Link className="btn secondary" to="/onboarding/entreprise/resume">
                Retour au résumé
              </Link>
            )}
          </div>
        </>
      )}
    </section>
  )
}
