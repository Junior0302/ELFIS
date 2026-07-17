import type { SubscriptionInfo, SubscriptionStatus } from './api'

export const subscriptionLabels: Record<SubscriptionStatus, string> = {
  trialing: 'Essai gratuit',
  active: 'Abonnement actif',
  past_due: 'Paiement à régulariser',
  unpaid: 'Impayé',
  canceled: 'Abonnement terminé',
  expired: 'Abonnement expiré',
  incomplete: 'Paiement incomplet',
  incomplete_expired: 'Paiement expiré',
  paused: 'Suspendu',
  none: 'Aucun abonnement',
  checkout_pending: 'Souscription non finalisée',
  cancel_scheduled: 'Résiliation programmée',
  admin_revoked: 'Accès suspendu',
}

export function subscriptionTone(status: SubscriptionStatus) {
  if (status === 'past_due' || status === 'incomplete' || status === 'checkout_pending') return 'warn'
  if (
    status === 'unpaid' ||
    status === 'expired' ||
    status === 'incomplete_expired' ||
    status === 'admin_revoked'
  ) {
    return 'danger'
  }
  if (status === 'canceled' || status === 'none' || status === 'paused' || status === 'cancel_scheduled') {
    return 'neutral'
  }
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
    'checkout_pending',
    'paused',
    'canceled',
    'cancel_scheduled',
  ].includes(status)
}

export function canStartSubscriptionCheckout(status: SubscriptionStatus) {
  return [
    'none',
    'canceled',
    'expired',
    'incomplete',
    'incomplete_expired',
    'checkout_pending',
    'admin_revoked',
  ].includes(status)
}

export function subscriptionCheckoutLabel(status: SubscriptionStatus, trialUsed?: boolean) {
  if (status === 'canceled' || status === 'expired') {
    return trialUsed ? 'Souscrire à nouveau (19 €/mois)' : 'Souscrire à nouveau'
  }
  if (status === 'incomplete' || status === 'checkout_pending') return 'Reprendre le paiement'
  if (status === 'incomplete_expired') return 'Relancer la souscription'
  if (trialUsed) return 'Souscrire à ComptaPilot IA — 19 €/mois'
  return 'Commencer mon essai gratuit de 14 jours'
}

export function subscriptionDeadline(subscription: SubscriptionInfo | null | undefined) {
  if (!subscription) return null
  if (subscription.status === 'trialing') {
    return subscription.trial_end || subscription.current_period_end || null
  }
  if (subscription.status === 'cancel_scheduled') {
    return subscription.access_ends_at || subscription.current_period_end || null
  }
  if (subscription.status === 'past_due') {
    return subscription.grace_until || subscription.current_period_end || null
  }
  return subscription.current_period_end || subscription.trial_end || null
}

export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(new Date(value))
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long', timeStyle: 'short' }).format(
    new Date(value),
  )
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
  return false
}

export function statusMessage(subscription: SubscriptionInfo): string {
  if (subscription.label) return subscription.label
  return subscriptionLabels[subscription.status] || subscription.status
}
