import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import { remainingTime } from '../subscription'

function bannerMessage(subscription: SubscriptionInfo, now: number) {
  switch (subscription.status) {
    case 'trialing':
      return `Essai Pro en cours · ${remainingTime(subscription.trial_end, now) ?? 'échéance à confirmer'} restant`
    case 'past_due':
      return 'Le dernier paiement a échoué. Mettez votre moyen de paiement à jour.'
    case 'unpaid':
      return 'Votre abonnement présente un impayé. Une action est requise.'
    case 'incomplete':
      return 'Le paiement initial doit être finalisé dans Stripe.'
    case 'incomplete_expired':
      return 'Le paiement initial a expiré. Relancez votre souscription.'
    case 'paused':
      return 'Votre abonnement est suspendu. Consultez le portail Stripe pour le reprendre.'
    case 'canceled':
      return 'Votre abonnement est résilié. Vous pouvez souscrire à nouveau.'
    case 'expired':
      return 'Votre abonnement a expiré. Une nouvelle souscription est nécessaire.'
    case 'none':
      return 'Activez l’essai Pro de 14 jours pour utiliser toutes les fonctionnalités.'
    default:
      return 'Votre abonnement n’est pas actif. Une action est requise.'
  }
}

export default function SubscriptionBanner() {
  const { token, orgId, memberships } = useAuth()
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    if (!token || !orgId) {
      setSubscription(null)
      return
    }
    let active = true
    api
      .currentSubscription(token, orgId)
      .then((result) => {
        if (active) setSubscription(result)
      })
      .catch(() => {
        if (active) setSubscription(null)
      })
    return () => {
      active = false
    }
  }, [token, orgId])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  if (!subscription || subscription.status === 'active') return null

  const activeMembership = memberships.find((membership) => membership.organization_id === orgId)
  const canManage = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )

  return (
    <div className={`global-subscription-banner ${subscription.status}`} role="status">
      <span>{bannerMessage(subscription, now)}</span>
      {canManage ? (
        <Link to="/abonnement">Voir l’abonnement</Link>
      ) : (
        <small>Contactez votre administrateur.</small>
      )}
    </div>
  )
}
