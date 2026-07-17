import { useCallback, useEffect, useState } from 'react'
import { api, formatEuro, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import {
  canOpenSubscriptionPortal,
  canStartSubscriptionCheckout,
  countdownParts,
  formatDate,
  formatDateTime,
  hasProductAccess,
  remainingTime,
  subscriptionCheckoutLabel,
  subscriptionDeadline,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'

const FEATURES = [
  'Analyse intelligente de documents comptables',
  'Extraction des informations de factures',
  'Assistance comptable par intelligence artificielle',
  'Gestion des factures, devis, clients et catalogue',
  'Tableaux de bord, historique et exports',
]

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
      <p className="trial-countdown-date">Jusqu’au {formatDateTime(deadline)}</p>
    </div>
  )
}

function statusDescription(sub: SubscriptionInfo): string {
  switch (sub.status) {
    case 'none':
      return 'Votre compte est actif, mais aucun abonnement ComptaPilot IA n’est associé à ce compte.'
    case 'checkout_pending':
    case 'incomplete':
      return 'Votre souscription n’est pas encore finalisée. Aucun prélèvement actif n’a été confirmé.'
    case 'trialing':
      return `Votre essai gratuit est actif jusqu’au ${formatDateTime(sub.trial_end)}. À la fin, renouvellement automatique à 19 €/mois sauf annulation.`
    case 'cancel_scheduled':
      return `Votre abonnement a été résilié. Vous conservez l’accès jusqu’au ${formatDateTime(sub.access_ends_at || sub.current_period_end)}.`
    case 'past_due':
      return `Nous n’avons pas pu renouveler votre abonnement. Mettez à jour votre moyen de paiement avant le ${formatDate(sub.grace_until)}.`
    case 'admin_revoked':
      return `Accès suspendu par l’administration. Motif : ${sub.admin_revoked_reason_public || 'non précisé'}.`
    case 'canceled':
    case 'expired':
      return `Votre abonnement n’est plus actif. Vos données sont conservées ; les fonctionnalités premium sont désactivées.`
    default:
      return sub.label || subscriptionLabels[sub.status]
  }
}

export default function AbonnementPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'checkout' | 'portal' | 'sync' | null>(null)
  const [error, setError] = useState('')
  const [returnNotice, setReturnNotice] = useState('')
  const [now, setNow] = useState(Date.now())
  const [renewalOk, setRenewalOk] = useState(false)
  const [termsOk, setTermsOk] = useState(false)

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
            setReturnNotice('Essai activé. Votre accès ComptaPilot IA est ouvert.')
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
    const tickMs =
      subscription?.status === 'trialing' || subscription?.status === 'cancel_scheduled'
        ? 1000
        : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  const startAction = async (kind: 'checkout' | 'portal') => {
    if (!token || !orgId) return
    if (kind === 'checkout' && (!renewalOk || !termsOk)) {
      setError('Veuillez accepter le renouvellement automatique et les conditions.')
      return
    }
    setAction(kind)
    setError('')
    try {
      const result =
        kind === 'checkout'
          ? await api.createSubscriptionCheckout(token, orgId, {
              automatic_renewal_accepted: renewalOk,
              terms_accepted: termsOk,
            })
          : await api.createSubscriptionPortal(token, orgId)
      openStripe(result.url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Redirection Stripe impossible')
      setAction(null)
    }
  }

  const statusForActions = (subscription?.status || 'none') as SubscriptionInfo['status']
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
          <h2>Abonnement et facturation</h2>
          <p>Offre ComptaPilot IA — 19 € / mois, essai 14 jours, renouvellement automatique.</p>
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
                : subscription.label || subscriptionLabels[subscription.status]}
            </span>
            <strong>ComptaPilot IA · {formatEuro(subscription.price_eur || 19)} / mois</strong>
          </div>

          <p className="muted">{statusDescription(subscription)}</p>

          {isTrialing ? (
            <>
              <CountdownBoard deadline={deadline} now={now} label="Essai gratuit — temps restant" />
              <div className="dashboard-sub-strip warn" style={{ marginTop: '1rem' }}>
                <div>
                  <strong>Essai gratuit — {remainingTime(deadline, now) || '…'}</strong>
                  <span>
                    Premier prélèvement prévu le {formatDate(subscription.trial_end)} : 19 € ·
                    Renouvellement mensuel automatique
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="subscription-active-meta">
              <p>
                {subscription.status === 'cancel_scheduled' ? 'Fin d’accès' : 'Prochaine échéance'} :{' '}
                <strong>{formatDate(deadline)}</strong>
              </p>
              {deadline && <p className="muted">{remainingTime(deadline, now)} restant</p>}
              {subscription.next_billing_amount_cents != null &&
                subscription.status !== 'cancel_scheduled' && (
                  <p className="muted">
                    Montant prévu : {formatEuro(subscription.next_billing_amount_cents / 100)}
                  </p>
                )}
            </div>
          )}

          <div className="subscription-active-actions">
            {canUsePortal && canManage && (
              <button
                className="btn"
                type="button"
                disabled={Boolean(action)}
                onClick={() => void startAction('portal')}
              >
                {action === 'portal' ? 'Ouverture…' : 'Gérer la carte, annuler ou factures'}
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
            <h3>ComptaPilot IA</h3>
            <div className="pricing-amount">
              <strong>19 €</strong>
              <span>/ mois</span>
            </div>
            <p className="muted">
              14 jours d’essai gratuit · Renouvellement mensuel automatique · Annulation avant
              échéance
            </p>
            <ul className="pricing-features">
              {FEATURES.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>

            {canCheckout && canManage && (
              <div className="subscription-consents">
                <label className="checkbox-inline">
                  <input
                    type="checkbox"
                    checked={renewalOk}
                    onChange={(e) => setRenewalOk(e.target.checked)}
                  />
                  J’ai compris que je bénéficie d’un essai gratuit de 14 jours et qu’à son terme,
                  mon abonnement sera automatiquement renouvelé au tarif de 19 € par mois, sauf
                  annulation avant la fin de l’essai.
                </label>
                <label className="checkbox-inline">
                  <input
                    type="checkbox"
                    checked={termsOk}
                    onChange={(e) => setTermsOk(e.target.checked)}
                  />
                  J’accepte les conditions générales d’utilisation, les conditions de l’abonnement
                  et la politique de confidentialité.
                </label>
                <button
                  className="btn subscription-main-action"
                  type="button"
                  disabled={Boolean(action) || subscription?.configured === false || !renewalOk || !termsOk}
                  onClick={() => void startAction('checkout')}
                >
                  {action === 'checkout'
                    ? 'Ouverture de Stripe…'
                    : subscription?.configured === false
                      ? 'Paiement bientôt disponible'
                      : subscriptionCheckoutLabel(
                          subscription!.status,
                          subscription?.trial_used,
                        )}
                </button>
                <p className="muted" style={{ marginTop: '0.75rem', fontSize: '0.88rem' }}>
                  Aucun prélèvement aujourd’hui. Premier prélèvement prévu dans 14 jours : 19 €,
                  puis 19 € par mois jusqu’à résiliation.
                </p>
              </div>
            )}
            {!canManage && (
              <p className="muted">
                Contactez le propriétaire de l’organisation pour modifier l’abonnement.
              </p>
            )}
          </section>

          <section className="panel subscription-status-card">
            <h3>Statut actuel</h3>
            {subscription ? (
              <>
                <div className="subscription-status-line">
                  <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                    {subscription.label || subscriptionLabels[subscription.status]}
                  </span>
                </div>
                <p className="muted" style={{ marginTop: '1rem' }}>
                  {statusDescription(subscription)}
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
