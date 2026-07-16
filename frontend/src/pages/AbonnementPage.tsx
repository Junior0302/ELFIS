import { useCallback, useEffect, useState } from 'react'
import { api, formatEuro, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import {
  canOpenSubscriptionPortal,
  canStartSubscriptionCheckout,
  countdownParts,
  formatDate,
  hasProductAccess,
  remainingTime,
  subscriptionCheckoutLabel,
  subscriptionDeadline,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'

function openStripe(url: string) {
  const target = new URL(url, window.location.origin)
  if (!['http:', 'https:'].includes(target.protocol)) {
    throw new Error('URL Stripe invalide')
  }
  window.location.assign(target.toString())
}

function CountdownBoard({
  deadline,
  now,
  label,
}: {
  deadline: string | null
  now: number
  label: string
}) {
  const parts = countdownParts(deadline, now)
  if (!parts) {
    return <p className="muted">Échéance non disponible pour le moment.</p>
  }
  if (parts.ended) {
    return (
      <div className="trial-countdown ended">
        <span className="trial-countdown-label">{label}</span>
        <strong>Terminé</strong>
      </div>
    )
  }
  return (
    <div className="trial-countdown">
      <span className="trial-countdown-label">{label}</span>
      <div className="trial-countdown-grid" aria-label={remainingTime(deadline, now) || undefined}>
        <div>
          <strong>{parts.days}</strong>
          <span>jours</span>
        </div>
        <div>
          <strong>{String(parts.hours).padStart(2, '0')}</strong>
          <span>heures</span>
        </div>
        <div>
          <strong>{String(parts.minutes).padStart(2, '0')}</strong>
          <span>min</span>
        </div>
        <div>
          <strong>{String(parts.seconds).padStart(2, '0')}</strong>
          <span>sec</span>
        </div>
      </div>
      <p className="trial-countdown-date">Jusqu’au {formatDate(deadline)}</p>
    </div>
  )
}

export default function AbonnementPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'checkout' | 'portal' | 'sync' | null>(null)
  const [error, setError] = useState('')
  const [returnNotice, setReturnNotice] = useState('')
  const [now, setNow] = useState(Date.now())

  const loadSubscription = useCallback(
    async (checkoutReturn?: 'success' | 'cancel', sessionId?: string | null) => {
      if (!token || !orgId) return
      setLoading(true)
      setError('')
      try {
        let current = await api.currentSubscription(token, orgId)
        if (checkoutReturn === 'success') {
          let syncError = ''
          try {
            current = await api.syncSubscription(token, orgId, sessionId)
          } catch (reason) {
            syncError = reason instanceof Error ? reason.message : 'Synchronisation Stripe impossible'
          }
          if (!hasProductAccess(current)) {
            await new Promise((resolve) => window.setTimeout(resolve, 1800))
            try {
              current = await api.syncSubscription(token, orgId, sessionId)
              syncError = ''
            } catch (reason) {
              syncError =
                reason instanceof Error ? reason.message : 'Synchronisation Stripe impossible'
              current = await api.currentSubscription(token, orgId)
            }
          }
          if (hasProductAccess(current)) {
            setReturnNotice('Essai activé. Votre accès ComptaPilot Pro est ouvert.')
          } else {
            setReturnNotice(
              syncError
                ? `Retour Stripe reçu, mais la sync a échoué : ${syncError}`
                : 'Retour de Stripe confirmé. Cliquez sur « Actualiser » pour forcer la synchro.',
            )
            if (syncError) setError(syncError)
          }
        } else if (checkoutReturn === 'cancel') {
          setReturnNotice('Paiement interrompu.')
        }
        setSubscription(current)
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Abonnement indisponible')
      } finally {
        setLoading(false)
      }
    },
    [token, orgId],
  )

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    let checkoutReturn: 'success' | 'cancel' | undefined
    const sessionId = params.get('session_id')
    if (params.has('success') || params.get('checkout') === 'success') {
      checkoutReturn = 'success'
    } else if (params.has('canceled') || params.get('checkout') === 'cancel') {
      checkoutReturn = 'cancel'
    }
    if (checkoutReturn) setReturnNotice('Vérification du statut…')
    if (params.size > 0) window.history.replaceState({}, '', window.location.pathname)
    void loadSubscription(checkoutReturn, sessionId)
  }, [loadSubscription])

  useEffect(() => {
    const tickMs = subscription?.status === 'trialing' ? 1000 : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  const startAction = async (kind: 'checkout' | 'portal') => {
    if (!token || !orgId) return
    setAction(kind)
    setError('')
    try {
      const result =
        kind === 'checkout'
          ? await api.createSubscriptionCheckout(token, orgId)
          : await api.createSubscriptionPortal(token, orgId)
      openStripe(result.url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Redirection Stripe impossible')
      setAction(null)
    }
  }

  const statusForActions = (subscription?.raw_status ||
    subscription?.status) as SubscriptionInfo['status']
  const canUsePortal =
    subscription &&
    !subscription.platform_bypass &&
    canOpenSubscriptionPortal(statusForActions)
  const canCheckout =
    subscription &&
    !hasProductAccess(subscription) &&
    canStartSubscriptionCheckout(statusForActions)
  const activeMembership = memberships.find((membership) => membership.organization_id === orgId)
  const canManage = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const isElfAdmin = Boolean(user?.is_platform_admin || subscription?.platform_bypass)
  const deadline = subscriptionDeadline(subscription)
  const isTrialing = subscription?.status === 'trialing'
  const isActiveAccess = hasProductAccess(subscription)

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Abonnement</h2>
          <p>
            {isTrialing
              ? 'Votre essai Pro est actif. Voici le temps restant avant la facturation.'
              : isActiveAccess
                ? 'Votre abonnement ComptaPilot Pro est actif.'
                : 'Démarrez l’essai de 14 jours pour ouvrir tout le produit.'}
          </p>
        </div>
      </div>

      {returnNotice && <div className="subscription-return">{returnNotice}</div>}
      {isElfAdmin && (
        <div className="subscription-return">
          Compte ELF Admin : accès complet, sans abonnement Stripe requis.
        </div>
      )}
      {error && <div className="auth-alert auth-alert-error">{error}</div>}

      {loading ? (
        <div className="loading">Vérification du statut…</div>
      ) : isActiveAccess && subscription ? (
        <section className="panel subscription-active-panel">
          <div className="subscription-status-line">
            <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
              {subscription.platform_bypass
                ? 'Accès ELF Admin'
                : subscriptionLabels[subscription.status]}
            </span>
            <strong>ComptaPilot Pro · {formatEuro(subscription.price_eur || 19)} / mois</strong>
          </div>

          {isTrialing ? (
            <CountdownBoard deadline={deadline} now={now} label="Temps restant d’essai" />
          ) : (
            <div className="subscription-active-meta">
              <p>
                Prochaine échéance : <strong>{formatDate(deadline)}</strong>
              </p>
              {deadline && <p className="muted">{remainingTime(deadline, now)} restant</p>}
            </div>
          )}

          {subscription.cancel_at_period_end && (
            <p className="muted">Résiliation prévue à la fin de la période en cours.</p>
          )}

          <div className="subscription-active-actions">
            {canUsePortal && canManage && (
              <button
                className="btn"
                type="button"
                disabled={Boolean(action)}
                onClick={() => void startAction('portal')}
              >
                {action === 'portal' ? 'Ouverture…' : 'Gérer la carte et les factures'}
              </button>
            )}
            {canManage && (
              <button
                className="btn secondary"
                type="button"
                disabled={Boolean(action)}
                onClick={() => {
                  setAction('sync')
                  void (async () => {
                    try {
                      setSubscription(await api.syncSubscription(token!, orgId))
                      setReturnNotice('Statut à jour.')
                    } catch (reason) {
                      setError(
                        reason instanceof Error ? reason.message : 'Synchronisation impossible',
                      )
                    } finally {
                      setAction(null)
                    }
                  })()
                }}
              >
                {action === 'sync' ? 'Actualisation…' : 'Actualiser'}
              </button>
            )}
          </div>
        </section>
      ) : (
        <div className="subscription-grid">
          <section className="panel pricing-card">
            <span className="home-eyebrow">Offre unique</span>
            <h3>ComptaPilot Pro</h3>
            <div className="pricing-amount">
              <strong>19 €</strong>
              <span>/ mois</span>
            </div>
            <p className="muted">14 jours d’essai, puis 19 € / mois. Carte demandée au départ.</p>
            <ul className="pricing-features">
              <li>Pilotage financier et comptable</li>
              <li>Copilote IA</li>
              <li>Facturation, OCR et exports</li>
              <li>Gestion d’équipe</li>
            </ul>
            {canCheckout && canManage && (
              <button
                className="btn subscription-main-action"
                type="button"
                disabled={Boolean(action) || subscription?.configured === false}
                onClick={() => void startAction('checkout')}
              >
                {action === 'checkout'
                  ? 'Ouverture de Stripe…'
                  : subscription?.configured === false
                    ? 'Paiement bientôt disponible'
                    : subscriptionCheckoutLabel(subscription!.status)}
              </button>
            )}
            {!canManage && (
              <p className="muted">
                Contactez le propriétaire de l’organisation pour modifier l’abonnement. En tant que
                membre, vous utilisez le plan de l’organisation — aucun abonnement personnel n’est
                requis.
              </p>
            )}
          </section>

          <section className="panel subscription-status-card">
            <h3>Statut actuel</h3>
            {subscription ? (
              <>
                <div className="subscription-status-line">
                  <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                    {subscriptionLabels[subscription.status]}
                  </span>
                </div>
                <p className="muted" style={{ marginTop: '1rem' }}>
                  Aucun essai actif pour cette organisation.
                </p>
                {canManage && (
                  <button
                    className="btn secondary"
                    type="button"
                    disabled={Boolean(action)}
                    style={{ marginTop: '1rem' }}
                    onClick={() => {
                      setAction('sync')
                      void (async () => {
                        try {
                          setSubscription(await api.syncSubscription(token!, orgId))
                        } catch (reason) {
                          setError(
                            reason instanceof Error ? reason.message : 'Synchronisation impossible',
                          )
                        } finally {
                          setAction(null)
                        }
                      })()
                    }}
                  >
                    {action === 'sync' ? 'Actualisation…' : 'Actualiser depuis Stripe'}
                  </button>
                )}
              </>
            ) : (
              <p className="muted">Statut indisponible.</p>
            )}
          </section>
        </div>
      )}
    </>
  )
}
