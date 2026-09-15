/** Convertit YYYY-MM-DD → DD-MM-YYYY (format stocké BE). */
export function isoDateToPaidAt(iso: string): string {
  const [y, m, d] = iso.split('-')
  if (!y || !m || !d) return iso
  return `${d}-${m}-${y}`
}
