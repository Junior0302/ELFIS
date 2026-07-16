import { useCallback, useEffect, useState } from 'react'
import { api, formatEuro, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import {
  canOpenSubscriptionPortal,
  canStartSubscriptionCheckout,
  formatDate,
  remainingTime,
  subscriptionCheckoutLabel,
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

export default function AbonnementPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'checkout' | 'portal' | 'sync' | null>(null)
  const [error, setError] = useState('')
  const [returnNotice, setReturnNotice] = useState('')
  const [now, setNow] = useState(Date.now())

  const loadSubscription = useCallback(async (checkoutReturn?: 'success' | 'cancel', sessionId?: string | null) => {
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
        if (!current?.access_granted && !['trialing', 'active'].includes(current?.status || '')) {
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
        const opened =
          Boolean(current?.access_granted) ||
          ['trialing', 'active'].includes(current?.status || '')
        if (opened) {
          setReturnNotice('Essai activé. Votre accès ComptaPilot Pro est ouvert.')
        } else {
          setReturnNotice(
            syncError
              ? `Retour Stripe reçu, mais la sync a échoué : ${syncError}`
              : 'Retour de Stripe confirmé. Cliquez sur « Actualiser le statut Stripe » pour forcer la synchro.',
          )
          if (syncError) setError(syncError)
        }
      } else if (checkoutReturn === 'cancel') {
        setReturnNotice('Paiement interrompu. Le statut affiché a été revérifié auprès du serveur.')
      }
      setSubscription(current)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Abonnement indisponible')
      if (checkoutReturn) {
        setReturnNotice(
          'Retour de Stripe détecté, mais le serveur n’a pas pu confirmer le statut. Réessayez dans un instant.',
        )
      }
    } finally {
      setLoading(false)
    }
  }, [token, orgId])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    let checkoutReturn: 'success' | 'cancel' | undefined
    const sessionId = params.get('session_id')
    if (params.has('success') || params.get('checkout') === 'success') {
      checkoutReturn = 'success'
    } else if (params.has('canceled') || params.get('checkout') === 'cancel') {
      checkoutReturn = 'cancel'
    }
    if (checkoutReturn) setReturnNotice('Retour de Stripe détecté. Vérification du statut en cours…')
    if (params.size > 0) window.history.replaceState({}, '', window.location.pathname)
    void loadSubscription(checkoutReturn, sessionId)
  }, [loadSubscription])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

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
    !subscription.access_granted &&
    canStartSubscriptionCheckout(statusForActions)
  const activeMembership = memberships.find((membership) => membership.organization_id === orgId)
  const canManage = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const isElfAdmin = Boolean(user?.is_platform_admin || subscription?.platform_bypass)
  const deadline =
    subscription?.status === 'trialing'
      ? subscription.trial_end
      : subscription?.current_period_end ?? null
  const deadlineLabel =
    subscription?.status === 'trialing'
      ? 'Fin de l’essai'
      : subscription?.status === 'canceled' || subscription?.status === 'expired'
        ? 'Fin d’accès'
        : 'Prochaine échéance'

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Abonnement</h2>
          <p>Une offre claire, sans engagement annuel. Stripe sécurise la carte et les paiements.</p>
        </div>
      </div>

      {returnNotice && <div className="subscription-return">{returnNotice}</div>}
      {isElfAdmin && (
        <div className="subscription-return">
          Compte ELF Admin : accès complet au produit, sans abonnement Stripe requis.
        </div>
      )}
      {error && <div className="auth-alert auth-alert-error">{error}</div>}

      <div className="subscription-grid">
        <section className="panel pricing-card">
          <span className="home-eyebrow">Offre unique</span>
          <h3>ComptaPilot Pro</h3>
          <div className="pricing-amount">
            <strong>19 €</strong>
            <span>/ mois</span>
          </div>
          <p className="muted">14 jours d’essai, puis facturation mensuelle. Carte demandée au départ.</p>
          <ul className="pricing-features">
            <li>Pilotage financier et comptable</li>
            <li>Copilote IA connecté à vos données</li>
            <li>Facturation, OCR et exports</li>
            <li>Gestion de votre équipe</li>
          </ul>
          {!loading && canCheckout && canManage && (
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
                  : subscriptionCheckoutLabel(subscription.status)}
            </button>
          )}
          {!loading && !canManage && (
            <p className="subscription-trust">
              Seul un propriétaire ou un administrateur peut démarrer et gérer l’abonnement.
            </p>
          )}
        </section>

        <section className="panel subscription-status-card">
          <h3>Votre abonnement</h3>
          {loading ? (
            <div className="loading">Vérification du statut…</div>
          ) : subscription ? (
            <>
              <div className="subscription-status-line">
                <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                  {subscription.platform_bypass
                    ? 'Accès ELF Admin'
                    : subscriptionLabels[subscription.status]}
                </span>
                <strong>{subscription.plan || 'Pro'}</strong>
              </div>
              <dl className="subscription-details">
                <div>
                  <dt>Tarif</dt>
                  <dd>{formatEuro(subscription.price_eur || 19)} / mois</dd>
                </div>
                {deadline && (
                  <>
                    <div>
                      <dt>{deadlineLabel}</dt>
                      <dd>{formatDate(deadline)}</dd>
                    </div>
                    <div>
                      <dt>Compte à rebours</dt>
                      <dd>{remainingTime(deadline, now)}</dd>
                    </div>
                  </>
                )}
                {subscription.cancel_at_period_end && (
                  <div>
                    <dt>Résiliation</dt>
                    <dd>Prévue à la fin de la période</dd>
                  </div>
                )}
              </dl>
              {canManage && (
                <button
                  className="btn secondary"
                  type="button"
                  disabled={Boolean(action) || loading}
                  onClick={() => {
                    setAction('sync')
                    void (async () => {
                      try {
                        setSubscription(await api.syncSubscription(token!, orgId))
                        setReturnNotice('Statut resynchronisé depuis Stripe.')
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
                  {action === 'sync' ? 'Synchronisation…' : 'Actualiser le statut Stripe'}
                </button>
              )}
              {canUsePortal && canManage && (
                <button
                  className="btn secondary"
                  type="button"
                  disabled={Boolean(action)}
                  onClick={() => void startAction('portal')}
                >
                  {action === 'portal'
                    ? 'Ouverture…'
                    : subscription.status === 'paused'
                      ? 'Reprendre depuis le portail Stripe'
                      : subscription.status === 'incomplete'
                        ? 'Finaliser le paiement'
                        : 'Gérer la carte et les factures'}
                </button>
              )}
            </>
          ) : (
            <p className="muted">Aucun abonnement n’a pu être affiché.</p>
          )}
          <p className="subscription-trust">
            Le statut affiché vient de l’API. Les paramètres de retour Stripe ne servent jamais de
            preuve de paiement.
          </p>
        </section>
      </div>
    </>
  )
}
