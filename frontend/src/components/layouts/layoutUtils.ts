/** Helpers partagés entre shells (avatar / initiales). */

export function userInitials(first?: string, last?: string) {
  const a = (first || '').trim().charAt(0)
  const b = (last || '').trim().charAt(0)
  return `${a}${b}`.toUpperCase() || '?'
}

export function safeAvatarUrl(url?: string | null) {
  if (!url) return ''
  const trimmed = url.trim()
  if (trimmed.startsWith('https://') || trimmed.startsWith('/')) return trimmed
  return ''
}
