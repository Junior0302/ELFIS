import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import { useSubscription } from '../subscriptionContext'
import {
  canStartSubscriptionCheckout,
  formatDate,
  hasProductAccess,
  remainingTime,
  subscriptionDeadline,
} from '../subscription'
import { trackProductEvent } from '../productEvents'

function bannerMessage(
  subscription: SubscriptionInfo,
  now: number,
  checkoutReturnPending: boolean,
  compactTrialOnboarding: boolean,
): string | null {
  if (checkoutReturnPending && !hasProductAccess(subscription)) {
    return 'Activation en cours… Votre accès sera confirmé dans un instant.'
  }

  if (compactTrialOnboarding && (subscription.status === 'none' || subscription.status === 'incomplete')) {
    return 'Votre essai gratuit n’est pas encore activé'
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
      return compactTrialOnboarding
        ? 'Finalisez votre activation pour débloquer ComptaPilot'
        : 'Paiement non finalisé. Reprenez la souscription sécurisée pour activer l’accès.'
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
      return compactTrialOnboarding
        ? 'Votre essai gratuit n’est pas encore activé'
        : 'Aucun abonnement associé à ce compte. Démarrez l’essai gratuit.'
    case 'active':
      return null
    default:
      if (hasProductAccess(subscription)) return null
      return 'Votre abonnement n’est pas actif. Une action est requise.'
  }
}

type Props = {
  /** Mode onboarding : bandeau discret, CTA essai, sans doublon verbeux. */
  compactTrialOnboarding?: boolean
}

export default function SubscriptionBanner({ compactTrialOnboarding = false }: Props) {
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

  const message = bannerMessage(subscription, now, checkoutReturnPending, compactTrialOnboarding)
  if (!message) return null

  const isTrialingUi =
    subscription.status === 'trialing' || subscription.status === 'cancel_scheduled'
  const needsTrialStart = canStartSubscriptionCheckout(subscription.status)
  const canManage = Boolean(
    memberships.find((m) => m.organization_id === orgId)?.permissions.includes('*') ||
      memberships
        .find((m) => m.organization_id === orgId)
        ?.permissions.includes('subscription.manage'),
  )

  const toneClass = compactTrialOnboarding
    ? 'trial-onboarding-banner'
    : subscription.status === 'trialing'
      ? 'trialing'
      : checkoutReturnPending
        ? 'none'
        : subscription.status

  const ctaLabel = isTrialingUi
    ? 'Détails'
    : needsTrialStart
      ? subscription.status === 'none' || !subscription.trial_used
        ? 'Démarrer mon essai gratuit'
        : 'Souscrire'
      : 'Gérer mon abonnement'

  return (
    <div
      className={`global-subscription-banner ${toneClass}`}
      role="status"
    >
      <span>{message}</span>
      {canManage ? (
        <Link
          to="/abonnement"
          onClick={() => {
            if (needsTrialStart) {
              trackProductEvent('trial_cta_clicked', { source: 'banner' })
            }
          }}
        >
          {ctaLabel}
          {compactTrialOnboarding && needsTrialStart ? ' →' : ''}
        </Link>
      ) : null}
    </div>
  )
}
