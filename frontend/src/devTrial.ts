import type { SubscriptionInfo } from './api'
import { resolveProductPhase } from './productPhase'

export type DevTrialStatus = {
  allowed: boolean
  environment: string
  flag_enabled: boolean
  reason: string | null
  already_active: boolean
}

export type DevTrialPanelMode =
  | 'loading'
  | 'allowed'
  | 'unavailable'
  | 'already_active'

/** Visibilité UI — le flag backend est vérifié via GET /api/dev/trial-status. */
export function shouldShowDevTrialButton(
  configured: boolean | undefined | null,
  isDev: boolean = import.meta.env.DEV,
): boolean {
  return Boolean(isDev) && configured === false
}

export function resolveDevTrialPanelMode(input: {
  statusLoading: boolean
  status: DevTrialStatus | null
  subscription: SubscriptionInfo | null | undefined
  isPlatformAdmin?: boolean
}): DevTrialPanelMode {
  if (
    isEntitledAfterRefresh(input.subscription, {
      isPlatformAdmin: input.isPlatformAdmin,
    }) ||
    input.status?.already_active
  ) {
    return 'already_active'
  }
  if (input.statusLoading || input.status == null) {
    return 'loading'
  }
  if (input.status.allowed) {
    return 'allowed'
  }
  return 'unavailable'
}

export function mapDevTrialError(reason: unknown): string {
  if (reason && typeof reason === 'object' && 'status' in reason) {
    const status = Number((reason as { status?: number }).status)
    const code = String((reason as { code?: string }).code || '')
    if (status === 401) return 'Votre session a expiré. Reconnectez-vous.'
    if (status === 404) return 'Activation locale indisponible sur ce serveur.'
    if (status === 409) return 'L’abonnement actuel ne permet pas d’activer un essai local.'
    if (status === 500) return 'Erreur serveur. Réessayez dans un instant.'
    if (
      status === 403 ||
      code === 'dev_trial_disabled' ||
      code === 'dev_trial_environment_forbidden' ||
      code === 'DEV_TRIAL_DISABLED'
    ) {
      return 'Le serveur n’autorise pas l’activation d’un essai local.'
    }
  }

  const raw =
    reason instanceof Error
      ? reason.message
      : typeof reason === 'string'
        ? reason
        : ''
  const lower = raw.toLowerCase()
  if (
    raw === 'DEV_TRIAL_DISABLED' ||
    lower.includes('dev_trial_disabled') ||
    lower.includes('dev_trial_environment_forbidden') ||
    lower.includes('elfis_dev_trial_enabled') ||
    lower.includes('mode développeur') ||
    lower.includes('développement désactiv')
  ) {
    return 'Le serveur n’autorise pas l’activation d’un essai local.'
  }
  if (raw === 'DEV_TRIAL_UNAUTHORIZED' || lower.includes('401')) {
    return 'Votre session a expiré. Reconnectez-vous.'
  }
  if (raw === 'DEV_TRIAL_CONFLICT' || lower.includes('409')) {
    return 'L’abonnement actuel ne permet pas d’activer un essai local.'
  }
  if (raw === 'DEV_TRIAL_NOT_FOUND' || lower.includes('404')) {
    return 'Activation locale indisponible sur ce serveur.'
  }
  if (raw === 'DEV_TRIAL_SERVER' || lower.includes('500')) {
    return 'Erreur serveur. Réessayez dans un instant.'
  }
  return 'Impossible d’activer l’essai local.'
}

export function isEntitledAfterRefresh(
  subscription: SubscriptionInfo | null | undefined,
  opts?: { isPlatformAdmin?: boolean },
): boolean {
  return resolveProductPhase(subscription, opts) === 'entitled'
}

export function logDevTrialFailure(meta: {
  status: number
  code?: string
  requestId?: string | null
}): void {
  if (!import.meta.env.DEV) return
  // eslint-disable-next-line no-console
  console.warn('[dev-trial]', {
    status: meta.status,
    code: meta.code || null,
    requestId: meta.requestId || null,
  })
}
