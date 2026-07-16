import type { SubscriptionStatus } from './api'

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

export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(new Date(value))
}

export function remainingTime(value: string | null | undefined, now = Date.now()) {
  if (!value) return null
  const remaining = new Date(value).getTime() - now
  if (remaining <= 0) return 'Terminé'
  const days = Math.floor(remaining / 86_400_000)
  const hours = Math.floor((remaining % 86_400_000) / 3_600_000)
  const minutes = Math.floor((remaining % 3_600_000) / 60_000)
  return `${days} j ${hours} h ${minutes} min`
}
