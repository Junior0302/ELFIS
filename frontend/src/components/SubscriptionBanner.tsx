import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import { formatDate, hasProductAccess, remainingTime, subscriptionDeadline } from '../subscription'

function bannerMessage(subscription: SubscriptionInfo, now: number) {
  const deadline = subscriptionDeadline(subscription)
  switch (subscription.status) {
    case 'trialing':
      return `Essai gratuit — ${remainingTime(deadline, now) || '…'} · Premier prélèvement le ${formatDate(subscription.trial_end)} : 19 €`
    case 'cancel_scheduled':
      return `Résiliation programmée — accès jusqu’au ${formatDate(subscription.access_ends_at || subscription.current_period_end)}`
    case 'past_due':
      return `Paiement en échec — régularisez avant le ${formatDate(subscription.grace_until)}`
    case 'checkout_pending':
    case 'incomplete':
      return 'Souscription non finalisée. Reprenez le paiement sécurisé.'
    case 'unpaid':
      return 'Votre abonnement présente un impayé. Une action est requise.'
    case 'paused':
      return 'Votre abonnement est suspendu. Consultez le portail Stripe pour le reprendre.'
    case 'admin_revoked':
      return `Accès suspendu : ${subscription.admin_revoked_reason_public || 'contactez le support'}`
    case 'canceled':
      return 'Votre abonnement est résilié. Vous pouvez souscrire à nouveau.'
    case 'expired':
      return 'Votre abonnement a expiré. Une nouvelle souscription est nécessaire.'
    case 'none':
      return 'Aucun abonnement associé à ce compte. Démarrez l’essai gratuit.'
    default:
      return 'Votre abonnement n’est pas actif. Une action est requise.'
  }
}

export default function SubscriptionBanner() {
  const { token, orgId, memberships } = useAuth()
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    if (!token || !orgId) return
    let cancelled = false
    void api
      .currentSubscription(token, orgId)
      .then((sub) => {
        if (!cancelled) setSubscription(sub)
      })
      .catch(() => {
        if (!cancelled) setSubscription(null)
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  useEffect(() => {
    const tickMs =
      subscription?.status === 'trialing' || subscription?.status === 'cancel_scheduled'
        ? 1000
        : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  if (!subscription || subscription.platform_bypass) return null
  if (subscription.status === 'active' && !subscription.cancel_at_period_end) return null
  if (subscription.status === 'trialing' || subscription.status === 'cancel_scheduled') {
    const canManage = Boolean(
      memberships.find((m) => m.organization_id === orgId)?.permissions.includes('*') ||
        memberships
          .find((m) => m.organization_id === orgId)
          ?.permissions.includes('subscription.manage'),
    )
    return (
      <div
        className={`global-subscription-banner ${subscription.status === 'trialing' ? 'trialing' : 'warn'}`}
        role="status"
      >
        <span>{bannerMessage(subscription, now)}</span>
        {canManage ? <Link to="/abonnement">Détails</Link> : null}
      </div>
    )
  }
  if (hasProductAccess(subscription)) return null

  const canManage = Boolean(
    memberships.find((m) => m.organization_id === orgId)?.permissions.includes('*') ||
      memberships
        .find((m) => m.organization_id === orgId)
        ?.permissions.includes('subscription.manage'),
  )

  return (
    <div className={`global-subscription-banner ${subscription.status}`} role="status">
      <span>{bannerMessage(subscription, now)}</span>
      {canManage ? <Link to="/abonnement">Voir l’abonnement</Link> : null}
    </div>
  )
}
