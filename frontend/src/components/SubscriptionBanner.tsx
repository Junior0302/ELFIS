import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import { useSubscription } from '../subscriptionContext'
import { formatDate, hasProductAccess, remainingTime, subscriptionDeadline } from '../subscription'

function bannerMessage(
  subscription: SubscriptionInfo,
  now: number,
  checkoutReturnPending: boolean,
): string | null {
  if (checkoutReturnPending && !hasProductAccess(subscription)) {
    return 'Activation en cours… Votre accès sera confirmé dans un instant.'
  }

  switch (subscription.status) {
    case 'trialing': {
      const deadline = subscriptionDeadline(subscription)
      return `Essai gratuit — ${remainingTime(deadline, now) || '…'} · Premier prélèvement le ${formatDate(subscription.trial_end)} : 19 €`
    }
    case 'cancel_scheduled':
      return `Résiliation programmée — accès jusqu’au ${formatDate(subscription.access_ends_at || subscription.current_period_end)}`
    case 'past_due':
      return `Paiement en échec — régularisez avant le ${formatDate(subscription.grace_until)}`
    case 'checkout_pending':
    case 'incomplete':
      return 'Paiement non finalisé. Reprenez la souscription sécurisée pour activer l’accès.'
    case 'unpaid':
      return 'Votre abonnement présente un impayé. Une action est requise.'
    case 'paused':
      return 'Votre abonnement est suspendu. Ouvrez l’espace facturation pour le reprendre.'
    case 'admin_revoked':
      return `Accès suspendu : ${subscription.admin_revoked_reason_public || 'contactez le support'}`
    case 'canceled':
      return 'Votre abonnement est résilié. Vous pouvez souscrire à nouveau.'
    case 'expired':
      return 'Votre abonnement a expiré. Une nouvelle souscription est nécessaire.'
    case 'none':
      return 'Aucun abonnement associé à ce compte. Démarrez l’essai gratuit.'
    case 'active':
      return null
    default:
      if (hasProductAccess(subscription)) return null
      return 'Votre abonnement n’est pas actif. Une action est requise.'
  }
}

export default function SubscriptionBanner() {
  const { orgId, memberships } = useAuth()
  const { subscription, checkoutReturnPending } = useSubscription()
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const tickMs =
      subscription?.status === 'trialing' || subscription?.status === 'cancel_scheduled'
        ? 1000
        : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  if (!subscription || subscription.platform_bypass) return null

  const message = bannerMessage(subscription, now, checkoutReturnPending)
  if (!message) return null

  const isTrialingUi =
    subscription.status === 'trialing' || subscription.status === 'cancel_scheduled'
  const canManage = Boolean(
    memberships.find((m) => m.organization_id === orgId)?.permissions.includes('*') ||
      memberships
        .find((m) => m.organization_id === orgId)
        ?.permissions.includes('subscription.manage'),
  )

  const toneClass =
    subscription.status === 'trialing'
      ? 'trialing'
      : checkoutReturnPending
        ? 'none'
        : subscription.status

  return (
    <div className={`global-subscription-banner ${toneClass}`} role="status">
      <span>{message}</span>
      {canManage ? (
        <Link to="/abonnement">{isTrialingUi ? 'Détails' : 'Voir l’abonnement'}</Link>
      ) : null}
    </div>
  )
}
