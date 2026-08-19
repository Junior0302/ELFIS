/**
 * Document Design System V1 — types & config unique (preview / download / email / Vault).
 */

export const DDS_TEMPLATE = 'premium_v1' as const

export type DocumentBrandingDraft = {
  showLogo: boolean
  template?: string
}

export type OrgDocumentBrandInput = {
  name?: string
  legal_name?: string
  logo?: string
  primary_color?: string
  secondary_color?: string
  address?: string
  postal_code?: string
  city?: string
  country?: string
  phone?: string
  email?: string
  website?: string
  siren?: string
  vat_number?: string
  share_capital?: string
  legal_form?: string
  legal_mentions?: string
  iban?: string
  bic?: string
  /** null/undefined = pas de préférence org */
  documents_show_logo?: boolean | null
}

export type DocumentRenderConfig = {
  showLogo: boolean
  template: string
  logoUrl: string
  hasLogo: boolean
  /** true si logo raster PDF-safe (pas SVG seul) */
  logoPdfSafe: boolean
  primaryColor: string
  secondaryColor: string
  displayName: string
  legalName: string
  orgNameStrong: string
  addressLines: string[]
  contactLines: string[]
  legalIdLines: string[]
  bankLines: string[]
  legalMentions: string
  footerParts: string[]
}

export type ResolveShowLogoInput = {
  draftShowLogo?: boolean | null
  orgPreference?: boolean | null
  hasPdfSafeLogo: boolean
}

/** Default : préférence org si existe, sinon Avec si logo valide, sinon Sans. */
export function resolveShowLogoDefault(input: ResolveShowLogoInput): boolean {
  if (typeof input.draftShowLogo === 'boolean') return input.draftShowLogo
  if (typeof input.orgPreference === 'boolean') return input.orgPreference
  return Boolean(input.hasPdfSafeLogo)
}

export function isPdfSafeLogoUrl(logoUrl: string | null | undefined): boolean {
  const raw = (logoUrl || '').trim()
  if (!raw) return false
  const lower = raw.toLowerCase()
  if (lower.includes('.svg')) return false
  return (
    lower.includes('.png') ||
    lower.includes('.jpg') ||
    lower.includes('.jpeg') ||
    lower.includes('.webp') ||
    lower.includes('/api/org/logos/')
  )
}

export function hasAnyLogoUrl(logoUrl: string | null | undefined): boolean {
  return Boolean((logoUrl || '').trim())
}

function buildAddressLines(org: OrgDocumentBrandInput): string[] {
  const lines: string[] = []
  const name = (org.legal_name || org.name || '').trim()
  if (name) lines.push(name)
  if (org.legal_form?.trim()) lines.push(org.legal_form.trim())
  if (org.address?.trim()) lines.push(org.address.trim())
  const cityLine = [org.postal_code?.trim(), org.city?.trim()].filter(Boolean).join(' ')
  if (cityLine) lines.push(cityLine)
  const country = (org.country || '').trim()
  if (country && !['FR', 'FRA', 'FRANCE'].includes(country.toUpperCase())) {
    lines.push(country)
  }
  return lines
}

function buildContactLines(org: OrgDocumentBrandInput): string[] {
  const lines: string[] = []
  if (org.phone?.trim()) lines.push(`Tél. ${org.phone.trim()}`)
  if (org.email?.trim()) lines.push(org.email.trim())
  if (org.website?.trim()) lines.push(org.website.trim())
  return lines
}

function buildLegalIdLines(org: OrgDocumentBrandInput): string[] {
  const lines: string[] = []
  const siren = (org.siren || '').trim()
  if (siren) lines.push(`${siren.length >= 14 ? 'SIRET' : 'SIREN'} ${siren}`)
  if (org.vat_number?.trim()) lines.push(`TVA ${org.vat_number.trim()}`)
  if (org.share_capital?.trim()) lines.push(`Capital ${org.share_capital.trim()}`)
  return lines
}

function buildBankLines(org: OrgDocumentBrandInput): string[] {
  const lines: string[] = []
  if (org.iban?.trim()) lines.push(`IBAN ${org.iban.trim()}`)
  if (org.bic?.trim()) lines.push(`BIC ${org.bic.trim()}`)
  return lines
}

export function buildDocumentRenderConfig(input: {
  org: OrgDocumentBrandInput | null | undefined
  branding?: DocumentBrandingDraft | null
}): DocumentRenderConfig {
  const org = input.org || {}
  const logoUrl = (org.logo || '').trim()
  const logoPdfSafe = isPdfSafeLogoUrl(logoUrl)
  const hasLogo = hasAnyLogoUrl(logoUrl)
  const showLogo = resolveShowLogoDefault({
    draftShowLogo: input.branding?.showLogo,
    orgPreference: org.documents_show_logo,
    hasPdfSafeLogo: logoPdfSafe || hasLogo,
  })
  const displayName = (org.name || '').trim()
  const legalName = (org.legal_name || '').trim()
  const orgNameStrong = legalName || displayName
  const addressLines = buildAddressLines(org)
  const contactLines = buildContactLines(org)
  const legalIdLines = buildLegalIdLines(org)
  const bankLines = buildBankLines(org)
  const legalMentions = (org.legal_mentions || '').trim()
  const footerParts = [
    orgNameStrong,
    [org.address?.trim(), [org.postal_code?.trim(), org.city?.trim()].filter(Boolean).join(' ')]
      .filter(Boolean)
      .join(', '),
    ...contactLines,
    ...legalIdLines,
    ...bankLines,
    legalMentions,
  ].filter(Boolean) as string[]

  const primary = (org.primary_color || '').trim()
  const secondary = (org.secondary_color || '').trim()

  return {
    showLogo,
    template: input.branding?.template || DDS_TEMPLATE,
    logoUrl,
    hasLogo,
    logoPdfSafe,
    primaryColor: primary.startsWith('#') ? primary : '#0B3D2E',
    secondaryColor: secondary.startsWith('#') ? secondary : '#E7F2EC',
    displayName,
    legalName,
    orgNameStrong,
    addressLines,
    contactLines,
    legalIdLines,
    bankLines,
    legalMentions,
    footerParts,
  }
}

export function partyBlockLabel(docType: string | null | undefined): string {
  if (docType === 'facture') return 'Facturé à'
  if (docType === 'avoir') return 'Crédit pour'
  return 'Destinataire'
}

export function docTypeTitle(docType: string | null | undefined): string {
  if (docType === 'devis') return 'Devis'
  if (docType === 'avoir') return 'Avoir'
  if (docType === 'facture') return 'Facture'
  return 'Document'
}
