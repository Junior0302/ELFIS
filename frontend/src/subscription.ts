import type { SubscriptionInfo, SubscriptionStatus } from './api'

export const subscriptionLabels: Record<SubscriptionStatus, string> = {
  trialing: 'Essai en cours',
  active: 'Actif',
  past_due: 'Paiement en retard',
  unpaid: 'Impayé',
  canceled: 'Résilié',
  expired: 'Expiré',
  incomplete: 'Paiement incomplet',
  incomplete_expired: 'Paiement expiré',
  paused: 'Suspendu',
  none: 'Aucun abonnement',
}

export function subscriptionTone(status: SubscriptionStatus) {
  if (status === 'past_due' || status === 'incomplete') return 'warn'
  if (status === 'unpaid' || status === 'expired' || status === 'incomplete_expired') return 'danger'
  if (status === 'canceled' || status === 'none' || status === 'paused') return 'neutral'
  return 'ok'
}

export function canOpenSubscriptionPortal(status: SubscriptionStatus) {
  return [
    'trialing',
    'active',
    'past_due',
    'unpaid',
    'incomplete',
    'incomplete_expired',
    'paused',
    'canceled',
  ].includes(status)
}

export function canStartSubscriptionCheckout(status: SubscriptionStatus) {
  return ['none', 'canceled', 'expired', 'incomplete', 'incomplete_expired'].includes(status)
}

export function subscriptionCheckoutLabel(status: SubscriptionStatus) {
  if (status === 'canceled' || status === 'expired') return 'Souscrire à nouveau'
  if (status === 'incomplete') return 'Reprendre le paiement'
  if (status === 'incomplete_expired') return 'Relancer la souscription'
  return 'Démarrer mon essai de 14 jours'
}

export function subscriptionDeadline(subscription: SubscriptionInfo | null | undefined) {
  if (!subscription) return null
  if (subscription.status === 'trialing') {
    return subscription.trial_end || subscription.current_period_end || null
  }
  return subscription.current_period_end || subscription.trial_end || null
}

export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(new Date(value))
}

export type CountdownParts = {
  totalMs: number
  days: number
  hours: number
  minutes: number
  seconds: number
  ended: boolean
}

export function countdownParts(value: string | null | undefined, now = Date.now()): CountdownParts | null {
  if (!value) return null
  const totalMs = new Date(value).getTime() - now
  if (Number.isNaN(totalMs)) return null
  if (totalMs <= 0) {
    return { totalMs: 0, days: 0, hours: 0, minutes: 0, seconds: 0, ended: true }
  }
  const days = Math.floor(totalMs / 86_400_000)
  const hours = Math.floor((totalMs % 86_400_000) / 3_600_000)
  const minutes = Math.floor((totalMs % 3_600_000) / 60_000)
  const seconds = Math.floor((totalMs % 60_000) / 1000)
  return { totalMs, days, hours, minutes, seconds, ended: false }
}

export function remainingTime(value: string | null | undefined, now = Date.now()) {
  const parts = countdownParts(value, now)
  if (!parts) return null
  if (parts.ended) return 'Terminé'
  if (parts.days > 0) return `${parts.days} j ${parts.hours} h ${parts.minutes} min`
  if (parts.hours > 0) return `${parts.hours} h ${parts.minutes} min ${parts.seconds} s`
  return `${parts.minutes} min ${parts.seconds} s`
}

export function hasProductAccess(subscription: SubscriptionInfo | null | undefined) {
  if (!subscription) return false
  if (subscription.platform_bypass || subscription.access_granted) return true
  return subscription.status === 'trialing' || subscription.status === 'active'
}
