/**
 * Traduction UX des erreurs HTTP — jamais de code brut côté client.
 * Les détails techniques restent dans la console (dev) / logs structurés.
 */

export type ApiErrorLogContext = {
  status: number
  endpoint: string
  organizationId?: number | null
  userId?: number | string | null
  requestId?: string | null
  detail?: string
}

const STATUS_MESSAGES: Record<number, string> = {
  401: 'Votre session a expiré. Reconnectez-vous pour continuer.',
  402: 'Cette fonctionnalité nécessite un essai ou un abonnement actif.',
  403: 'Vous n’avez pas l’autorisation d’accéder à cette ressource.',
  404: 'Cette ressource est indisponible pour le moment.',
  429: 'Trop de demandes. Réessayez dans quelques instants.',
  500: 'Le service est temporairement indisponible. Réessayez plus tard.',
  502: 'Le service est temporairement indisponible. Réessayez plus tard.',
  503: 'Le service est temporairement indisponible. Réessayez plus tard.',
}

/** Message humain actionnable — jamais « Erreur API 402 ». */
export function userFacingApiMessage(status: number, detail?: string): string {
  const mapped = STATUS_MESSAGES[status]
  if (mapped) return mapped
  if (detail && !/^erreur\s*api\s*\d+/i.test(detail) && !/^\d{3}$/.test(detail.trim())) {
    // Évite de remonter un détail technique type "Payment Required"
    const lower = detail.toLowerCase()
    if (
      lower.includes('subscription') ||
      lower.includes('abonnement') ||
      lower.includes('trial') ||
      lower.includes('essai') ||
      lower.includes('payment required')
    ) {
      return STATUS_MESSAGES[402]
    }
    return detail
  }
  return 'Une erreur est survenue. Réessayez ou contactez le support.'
}

export function logApiFailure(ctx: ApiErrorLogContext): void {
  // eslint-disable-next-line no-console
  console.warn('[ComptaPilot API]', {
    status: ctx.status,
    endpoint: ctx.endpoint,
    organizationId: ctx.organizationId ?? null,
    userId: ctx.userId ?? null,
    requestId: ctx.requestId ?? null,
    detail: ctx.detail ?? null,
  })
}

export function createApiError(
  status: number,
  detail: string | undefined,
  ctx: Omit<ApiErrorLogContext, 'status' | 'detail'>,
): Error & { status: number } {
  logApiFailure({ ...ctx, status, detail })
  const err = new Error(userFacingApiMessage(status, detail)) as Error & { status: number }
  err.status = status
  return err
}

/** Détecte un message déjà mappé ou un 402/subscription pour l’UI gate. */
export function isEntitlementError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const status = (error as { status?: number }).status
  if (status === 402) return true
  const message = error instanceof Error ? error.message : String(error)
  const lower = message.toLowerCase()
  return (
    lower.includes('essai') ||
    lower.includes('abonnement') ||
    lower.includes('subscription') ||
    lower.includes('entitlement')
  )
}
