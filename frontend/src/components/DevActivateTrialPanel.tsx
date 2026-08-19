import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  isEntitledAfterRefresh,
  logDevTrialFailure,
  mapDevTrialError,
  resolveDevTrialPanelMode,
  type DevTrialStatus,
} from '../devTrial'
import { POST_ENTITLEMENT_SETUP_PATH } from '../enterpriseSetup'
import { useSubscription } from '../subscriptionContext'

/**
 * Porte d’entrée vers POST /api/dev/activate-trial.
 * Ne doit être monté que sous import.meta.env.DEV (exclu du rendu prod).
 * La disponibilité réelle vient du backend (GET /api/dev/trial-status).
 */
export default function DevActivateTrialPanel() {
  const { token, orgId, user } = useAuth()
  const { subscription, refresh } = useSubscription()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [statusLoading, setStatusLoading] = useState(true)
  const [status, setStatus] = useState<DevTrialStatus | null>(null)
  const inflight = useRef(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      if (!token) {
        setStatusLoading(false)
        setStatus({
          allowed: false,
          environment: 'unknown',
          flag_enabled: false,
          reason: 'dev_trial_disabled',
          already_active: false,
        })
        return
      }
      setStatusLoading(true)
      try {
        const next = await api.getDevTrialStatus(token, orgId)
        if (!cancelled) setStatus(next)
      } catch {
        if (!cancelled) {
          setStatus({
            allowed: false,
            environment: 'unknown',
            flag_enabled: false,
            reason: 'dev_trial_disabled',
            already_active: false,
          })
        }
      } finally {
        if (!cancelled) setStatusLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  const mode = resolveDevTrialPanelMode({
    statusLoading,
    status,
    subscription,
    isPlatformAdmin: Boolean(user?.is_platform_admin),
  })

  const onActivate = async () => {
    if (inflight.current || busy || mode !== 'allowed') return
    if (!token || orgId == null) {
      setError('Impossible d’activer l’essai local.')
      return
    }
    inflight.current = true
    setBusy(true)
    setError('')
    try {
      await api.activateDevTrial(token, orgId)
      const updated = await refresh()
      if (
        isEntitledAfterRefresh(updated, {
          isPlatformAdmin: Boolean(user?.is_platform_admin),
        })
      ) {
        navigate(POST_ENTITLEMENT_SETUP_PATH, { replace: true })
      }
    } catch (reason) {
      if (reason && typeof reason === 'object' && 'status' in reason) {
        logDevTrialFailure({
          status: Number((reason as { status: number }).status),
          code: String((reason as { code?: string }).code || ''),
          requestId: (reason as { requestId?: string | null }).requestId,
        })
      }
      setError(mapDevTrialError(reason))
    } finally {
      inflight.current = false
      setBusy(false)
    }
  }

  if (mode === 'loading') {
    return (
      <aside className="dev-trial-panel" aria-label="Mode développement" aria-busy="true">
        <p className="dev-trial-panel-eyebrow">Mode développement</p>
        <p className="dev-trial-panel-text">Vérification de l’activation locale…</p>
      </aside>
    )
  }

  if (mode === 'already_active') {
    return (
      <aside className="dev-trial-panel" aria-label="Essai local actif">
        <p className="dev-trial-panel-eyebrow">Essai local actif</p>
        <p className="dev-trial-panel-text">
          Votre organisation dispose déjà d’un accès. Poursuivez la configuration.
        </p>
        <button
          type="button"
          className="btn secondary dev-trial-panel-action"
          onClick={() => navigate(POST_ENTITLEMENT_SETUP_PATH)}
        >
          Continuer la configuration
        </button>
      </aside>
    )
  }

  if (mode === 'unavailable') {
    return (
      <aside className="dev-trial-panel" aria-label="Activation locale indisponible">
        <p className="dev-trial-panel-eyebrow">Activation locale indisponible</p>
        <p className="dev-trial-panel-text">
          Le serveur n’autorise pas l’activation d’un essai local.
        </p>
        <p className="dev-trial-panel-text muted">
          En local : définir <code>ELFIS_DEV_TRIAL_ENABLED=true</code> dans{' '}
          <code>backend/.env</code>, avec <code>ELFIS_ENVIRONMENT=development</code>, puis
          redémarrer FastAPI.
        </p>
      </aside>
    )
  }

  return (
    <aside className="dev-trial-panel" aria-label="Mode développement">
      <p className="dev-trial-panel-eyebrow">Mode développement</p>
      <p className="dev-trial-panel-text">
        Stripe n’est pas configuré. Vous pouvez activer un essai local afin de tester
        l’application.
      </p>
      {error ? (
        <p className="dev-trial-panel-error" role="alert">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        className="btn secondary dev-trial-panel-action"
        disabled={busy}
        onClick={() => void onActivate()}
      >
        {busy ? 'Activation de l’essai…' : 'Activer un essai local'}
      </button>
    </aside>
  )
}
