/** Mentions légales minimales pour PDF / envoi commercial (P1-10). */

export type OrgLegalFields = {
  name?: string | null
  legal_name?: string | null
  siren?: string | null
  vat_number?: string | null
  address?: string | null
  postal_code?: string | null
  city?: string | null
  legal_mentions?: string | null
}

export type OrgLegalGap = {
  code: 'siren' | 'address' | 'legal_mentions' | 'identity'
  label: string
}

export function orgLegalGaps(org: OrgLegalFields | null | undefined): OrgLegalGap[] {
  if (!org) {
    return [{ code: 'identity', label: 'Organisation introuvable' }]
  }
  const gaps: OrgLegalGap[] = []
  const identity = (org.legal_name || org.name || '').trim()
  if (!identity) {
    gaps.push({ code: 'identity', label: 'Raison sociale / nom' })
  }
  const siren = (org.siren || '').replace(/\s/g, '')
  if (siren.length < 9) {
    gaps.push({ code: 'siren', label: 'SIREN / SIRET' })
  }
  const addressOk =
    Boolean((org.address || '').trim()) &&
    Boolean((org.postal_code || '').trim()) &&
    Boolean((org.city || '').trim())
  if (!addressOk) {
    gaps.push({ code: 'address', label: 'Adresse complète (rue, CP, ville)' })
  }
  // Mentions libres optionnelles si SIRET + adresse présents — signal soft seulement
  if (!(org.legal_mentions || '').trim() && gaps.length === 0) {
    gaps.push({ code: 'legal_mentions', label: 'Mentions légales libres (recommandé)' })
  }
  return gaps
}

export function orgLegalIsReadyForSend(org: OrgLegalFields | null | undefined): boolean {
  const gaps = orgLegalGaps(org)
  // Soft: mentions libres seules ne bloquent pas
  return gaps.every((g) => g.code === 'legal_mentions')
}
