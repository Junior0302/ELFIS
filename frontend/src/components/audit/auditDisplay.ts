import type { AuditEvent } from '../../types/audit'

const BLOCKED_META_KEYS = new Set([
  'jwt',
  'password',
  'passwd',
  'secret',
  'api_key',
  'apikey',
  'authorization',
  'access_token',
  'refresh_token',
  'id_token',
  'cookie',
  'cookies',
  'stripe_token',
  'stripe_signature',
  'vault_secret',
  'private_key',
  'ocr_text',
  'raw_text',
  'prompt',
  'completion',
  'ai_response',
  'full_text',
])

export function formatLocalTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'short',
      timeStyle: 'medium',
    })
  } catch {
    return iso
  }
}

export function formatUtcFull(iso: string): string {
  try {
    return `${new Date(iso).toISOString()} (UTC)`
  } catch {
    return iso
  }
}

export function maskIp(ip: string | null | undefined): string {
  if (!ip) return '—'
  const parts = ip.split('.')
  if (parts.length === 4) return `${parts[0]}.${parts[1]}.*.*`
  if (ip.includes(':')) {
    const segs = ip.split(':')
    return `${segs.slice(0, 2).join(':')}:*:*`
  }
  return ip.length > 8 ? `${ip.slice(0, 4)}…` : ip
}

export function simplifyUserAgent(ua: string | null | undefined): string {
  if (!ua) return '—'
  const cleaned = ua.trim()
  if (cleaned.length <= 80) return cleaned
  return `${cleaned.slice(0, 77)}…`
}

export function safeMetadataEntries(
  metadata: Record<string, unknown> | null | undefined,
): Array<[string, string]> {
  if (!metadata) return []
  const out: Array<[string, string]> = []
  for (const [key, value] of Object.entries(metadata)) {
    const lowered = key.toLowerCase().replace(/-/g, '_')
    if (BLOCKED_META_KEYS.has(lowered) || [...BLOCKED_META_KEYS].some((b) => lowered.includes(b))) {
      continue
    }
    if (value === null || value === undefined) continue
    if (typeof value === 'object') {
      out.push([key, '[objet]'])
      continue
    }
    const text = String(value)
    if (/bearer\s+/i.test(text) || /sk_(live|test)_/i.test(text)) continue
    out.push([key, text.length > 200 ? `${text.slice(0, 197)}…` : text])
  }
  return out.slice(0, 30)
}

export function narrativeForEvent(event: AuditEvent): string {
  const actor = event.actor_email || (event.actor_user_id != null ? `Utilisateur #${event.actor_user_id}` : null)
  const target = event.target_display || event.target_id
  const role = typeof event.metadata?.role_code === 'string' ? event.metadata.role_code : null
  const permission = typeof event.metadata?.permission === 'string' ? event.metadata.permission : null

  switch (event.action) {
    case 'LOGIN_SUCCESS':
      return actor ? `${actor} s'est connecté.` : 'Connexion réussie.'
    case 'LOGIN_FAILURE':
      return 'Une tentative de connexion a échoué.'
    case 'LOGOUT':
      return actor ? `${actor} s'est déconnecté.` : 'Déconnexion.'
    case 'ROLE_ASSIGNED':
      return actor && role && target
        ? `${actor} a attribué le rôle ${role} à ${target}.`
        : event.message || 'Rôle plateforme attribué.'
    case 'ROLE_REMOVED':
      return actor && role && target
        ? `${actor} a retiré le rôle ${role} de ${target}.`
        : event.message || 'Rôle plateforme retiré.'
    case 'PERMISSION_DENIED':
      return permission
        ? `L'accès à ${permission} a été refusé.`
        : 'Un accès a été refusé.'
    case 'HEALTH_REFRESH':
      return actor
        ? `${actor} a consulté System Health.`
        : 'System Health a été consulté.'
    default:
      return event.message || `${event.action}`
  }
}
