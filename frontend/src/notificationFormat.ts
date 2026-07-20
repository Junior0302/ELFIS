export type AppNotification = {
  notification_id: string
  notification_type: string
  category: string
  title: string
  message: string
  severity: string
  status: string
  action_url?: string | null
  action_label?: string | null
  related_entity_type?: string | null
  related_entity_id?: string | null
  created_at?: string | null
  read_at?: string | null
}

export function formatNotificationDate(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}

export function formatUnreadBadge(count: number): string {
  if (count <= 0) return ''
  if (count > 99) return '99+'
  return String(count)
}

export function severityLabel(severity: string): string {
  const map: Record<string, string> = {
    info: 'Info',
    success: 'Succès',
    warning: 'Attention',
    error: 'Erreur',
    critical: 'Critique',
  }
  return map[severity] || severity
}

export function categoryLabel(category: string): string {
  const map: Record<string, string> = {
    billing: 'Facturation',
    vault: 'Vault',
    email: 'E-mail',
    accounting: 'Comptabilité',
    security: 'Sécurité',
    subscription: 'Abonnement',
    system: 'Système',
  }
  return map[category] || category
}

export function isSafeInternalActionUrl(url?: string | null): boolean {
  if (!url) return false
  const trimmed = url.trim()
  if (!trimmed.startsWith('/')) return false
  if (trimmed.startsWith('//')) return false
  if (/[\s<>"']/.test(trimmed)) return false
  const lower = trimmed.toLowerCase()
  if (lower.startsWith('/javascript:') || lower.includes('javascript:')) return false
  return true
}
