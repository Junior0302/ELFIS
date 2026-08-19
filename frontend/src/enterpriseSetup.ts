/**
 * Enterprise Setup — parcours de configuration entreprise.
 * Draft frontend temporaire — pas de source de vérité backend.
 */

import {
  isValidCountryCode,
  normalizeCountryCode,
} from './countries'
import { isValidCurrencyCode, normalizeCurrencyCode } from './currencies'

export const ENTERPRISE_SETUP_PATH = '/onboarding/entreprise' as const
export const ENTERPRISE_SETUP_COMPANY_NAME_PATH = '/onboarding/entreprise/nom' as const
export const ENTERPRISE_SETUP_INDUSTRY_PATH = '/onboarding/entreprise/secteur' as const
export const ENTERPRISE_SETUP_COUNTRY_PATH = '/onboarding/entreprise/pays' as const
export const ENTERPRISE_SETUP_CURRENCY_PATH = '/onboarding/entreprise/devise' as const
export const ENTERPRISE_SETUP_VAT_PATH = '/onboarding/entreprise/tva' as const
export const ENTERPRISE_SETUP_SUMMARY_PATH = '/onboarding/entreprise/resume' as const
export const ENTERPRISE_SETUP_PREPARATION_PATH = '/onboarding/entreprise/preparation' as const
/** Ancienne route — redirige vers le résumé (C1.10). */
export const ENTERPRISE_SETUP_BANK_PATH = '/onboarding/entreprise/banque' as const

/** Bouton « Commencer la configuration » → première étape. */
export const ENTERPRISE_SETUP_START_PATH = ENTERPRISE_SETUP_COMPANY_NAME_PATH

/**
 * Destination après obtention d’un entitlement (essai / abo).
 */
export const POST_ENTITLEMENT_SETUP_PATH = ENTERPRISE_SETUP_PATH

export const ENTERPRISE_SETUP_DRAFT_STORAGE_KEY = 'elfis.enterprise_setup.draft'

export const COMPANY_NAME_MIN_LENGTH = 2
export const COMPANY_NAME_MAX_LENGTH = 120
export const INDUSTRY_OTHER_MIN_LENGTH = 2
export const INDUSTRY_OTHER_MAX_LENGTH = 100
export const VAT_NUMBER_MAX_LENGTH = 32

export const ENTERPRISE_SETUP_VAT_STATUSES = [
  {
    id: 'vat_registered',
    label: 'Oui, mon entreprise facture la TVA',
    description: 'La TVA est ajoutée à tout ou partie de mes ventes.',
  },
  {
    id: 'vat_not_registered',
    label: 'Non, mon entreprise ne facture pas la TVA',
    description: 'Je bénéficie d’une exonération, d’une franchise ou d’un régime sans TVA.',
  },
  {
    id: 'vat_unknown',
    label: 'Je ne sais pas encore',
    description: 'Je souhaite terminer la configuration et vérifier ce point plus tard.',
  },
] as const

export type EnterpriseSetupVatStatus = (typeof ENTERPRISE_SETUP_VAT_STATUSES)[number]['id']

const VAT_STATUS_SET = new Set<string>(ENTERPRISE_SETUP_VAT_STATUSES.map((item) => item.id))

export function isEnterpriseSetupVatStatus(value: string): value is EnterpriseSetupVatStatus {
  return VAT_STATUS_SET.has(value)
}

export const ENTERPRISE_SETUP_INDUSTRIES = [
  { id: 'commerce', label: 'Commerce' },
  { id: 'services', label: 'Services' },
  { id: 'construction', label: 'Bâtiment et travaux' },
  { id: 'transport_logistics', label: 'Transport et logistique' },
  { id: 'food_hospitality', label: 'Restauration et alimentation' },
  { id: 'automotive', label: 'Automobile' },
  { id: 'health_wellness', label: 'Santé et bien-être' },
  { id: 'real_estate', label: 'Immobilier' },
  { id: 'technology', label: 'Numérique et technologie' },
  { id: 'consulting_training', label: 'Conseil et formation' },
  { id: 'crafts', label: 'Artisanat' },
  { id: 'other', label: 'Autre' },
] as const

export type EnterpriseSetupIndustryId = (typeof ENTERPRISE_SETUP_INDUSTRIES)[number]['id']

const INDUSTRY_ID_SET = new Set<string>(ENTERPRISE_SETUP_INDUSTRIES.map((item) => item.id))

export function isEnterpriseSetupIndustryId(value: string): value is EnterpriseSetupIndustryId {
  return INDUSTRY_ID_SET.has(value)
}

export const ENTERPRISE_SETUP_STEPS = [
  { id: 'company_name', label: 'Nom de l’entreprise', path: ENTERPRISE_SETUP_COMPANY_NAME_PATH },
  { id: 'industry', label: 'Secteur d’activité', path: ENTERPRISE_SETUP_INDUSTRY_PATH },
  { id: 'country', label: 'Pays', path: ENTERPRISE_SETUP_COUNTRY_PATH },
  { id: 'currency', label: 'Devise', path: ENTERPRISE_SETUP_CURRENCY_PATH },
  { id: 'vat', label: 'TVA', path: ENTERPRISE_SETUP_VAT_PATH },
  { id: 'summary', label: 'Résumé de configuration', path: ENTERPRISE_SETUP_SUMMARY_PATH },
  { id: 'preparation', label: 'Préparation du workspace', path: ENTERPRISE_SETUP_PREPARATION_PATH },
  { id: 'completion', label: 'Dashboard', path: '/dashboard' },
] as const

export type EnterpriseSetupStepId = (typeof ENTERPRISE_SETUP_STEPS)[number]['id']

/** Libellés résumé (pas les IDs techniques). */
export const ENTERPRISE_SETUP_VAT_SUMMARY_LABELS: Record<EnterpriseSetupVatStatus, string> = {
  vat_registered: 'L’entreprise facture la TVA',
  vat_not_registered: 'L’entreprise ne facture pas la TVA',
  vat_unknown: 'À vérifier plus tard',
}

/** Draft C1.9 — champs futurs absents volontairement. */
export type EnterpriseSetupDraft = {
  company_name: string
  industry: string
  industry_other?: string
  country: string
  currency: string
  vat_status: string
  vat_number?: string
}

export function emptyEnterpriseSetupDraft(): EnterpriseSetupDraft {
  return { company_name: '', industry: '', country: '', currency: '', vat_status: '' }
}

export function isEnterpriseSetupPath(pathname: string): boolean {
  const trimmed = pathname.replace(/\/+$/, '') || '/'
  return (
    trimmed === ENTERPRISE_SETUP_PATH ||
    trimmed.startsWith(`${ENTERPRISE_SETUP_PATH}/`)
  )
}

export function firstEnterpriseSetupStepId(): EnterpriseSetupStepId {
  return ENTERPRISE_SETUP_STEPS[0].id
}

export function enterpriseSetupStepIndex(stepId: EnterpriseSetupStepId): number {
  return ENTERPRISE_SETUP_STEPS.findIndex((step) => step.id === stepId)
}

export function enterpriseSetupProgress(stepId: EnterpriseSetupStepId): {
  current: number
  total: number
  label: string
} {
  const index = enterpriseSetupStepIndex(stepId)
  const current = index >= 0 ? index + 1 : 1
  const total = ENTERPRISE_SETUP_STEPS.length
  return {
    current,
    total,
    label: `Étape ${current} sur ${total}`,
  }
}

export function normalizeCompanyName(raw: string): string {
  return raw.trim()
}

export function normalizeIndustryOther(raw: string): string {
  return raw.trim()
}

/** null = valide ; sinon message UX. */
export function validateCompanyName(raw: string): string | null {
  const value = normalizeCompanyName(raw)
  if (!value) return 'Indiquez le nom de votre entreprise.'
  if (value.length < COMPANY_NAME_MIN_LENGTH) {
    return 'Le nom doit contenir au moins 2 caractères.'
  }
  if (value.length > COMPANY_NAME_MAX_LENGTH) {
    return 'Le nom ne peut pas dépasser 120 caractères.'
  }
  return null
}

export function canSubmitCompanyName(raw: string): boolean {
  return validateCompanyName(raw) === null
}

export function validateIndustryOther(raw: string): string | null {
  const value = normalizeIndustryOther(raw)
  if (!value) return 'Précisez votre secteur d’activité.'
  if (value.length < INDUSTRY_OTHER_MIN_LENGTH) {
    return 'Le secteur doit contenir au moins 2 caractères.'
  }
  if (value.length > INDUSTRY_OTHER_MAX_LENGTH) {
    return 'Le secteur ne peut pas dépasser 100 caractères.'
  }
  return null
}

/** null = valide ; sinon message UX. */
export function validateIndustrySelection(
  industry: string,
  industryOther: string = '',
): string | null {
  if (!industry || !isEnterpriseSetupIndustryId(industry)) {
    return 'Sélectionnez votre secteur d’activité.'
  }
  if (industry === 'other') {
    return validateIndustryOther(industryOther)
  }
  return null
}

export function canSubmitIndustry(industry: string, industryOther: string = ''): boolean {
  return validateIndustrySelection(industry, industryOther) === null
}

export function validateCountry(raw: string): string | null {
  if (!raw || !isValidCountryCode(raw)) {
    return 'Sélectionnez le pays de votre entreprise.'
  }
  return null
}

export function canSubmitCountry(raw: string): boolean {
  return validateCountry(raw) === null
}

export function validateCurrency(raw: string): string | null {
  if (!raw || !isValidCurrencyCode(raw)) {
    return 'Sélectionnez la devise principale de votre entreprise.'
  }
  return null
}

export function canSubmitCurrency(raw: string): boolean {
  return validateCurrency(raw) === null
}

export function normalizeVatNumber(raw: string): string {
  return String(raw || '')
    .replace(/\s+/g, '')
    .trim()
    .toUpperCase()
    .slice(0, VAT_NUMBER_MAX_LENGTH)
}

/** null = valide (y compris vide) ; sinon message UX. */
export function validateVatNumber(raw: string): string | null {
  const trimmed = String(raw || '').trim()
  if (!trimmed) return null
  if (trimmed.replace(/\s+/g, '').length > VAT_NUMBER_MAX_LENGTH) {
    return 'Vérifiez le format du numéro de TVA.'
  }
  const normalized = normalizeVatNumber(raw)
  if (!/^[A-Z0-9]+$/.test(normalized)) {
    return 'Vérifiez le format du numéro de TVA.'
  }
  return null
}

export function validateVatStatus(
  status: string,
  vatNumber: string = '',
): string | null {
  if (!status || !isEnterpriseSetupVatStatus(status)) {
    return 'Indiquez si votre entreprise facture la TVA.'
  }
  if (status === 'vat_registered') {
    return validateVatNumber(vatNumber)
  }
  return null
}

export function canSubmitVatStatus(status: string, vatNumber: string = ''): boolean {
  return validateVatStatus(status, vatNumber) === null
}

export function getIndustryLabel(industry: string, industryOther: string = ''): string {
  if (industry === 'other') {
    const other = normalizeIndustryOther(industryOther)
    return other || 'Autre'
  }
  const found = ENTERPRISE_SETUP_INDUSTRIES.find((item) => item.id === industry)
  return found?.label ?? ''
}

export function getVatSummaryLabel(status: string): string {
  if (!isEnterpriseSetupVatStatus(status)) return ''
  return ENTERPRISE_SETUP_VAT_SUMMARY_LABELS[status]
}

/** Première étape invalide du draft, ou null si complet. */
export function firstIncompleteEnterpriseSetupPath(draft: EnterpriseSetupDraft): string | null {
  if (!canSubmitCompanyName(draft.company_name)) return ENTERPRISE_SETUP_COMPANY_NAME_PATH
  if (!canSubmitIndustry(draft.industry, draft.industry_other ?? '')) {
    return ENTERPRISE_SETUP_INDUSTRY_PATH
  }
  if (!canSubmitCountry(draft.country)) return ENTERPRISE_SETUP_COUNTRY_PATH
  if (!canSubmitCurrency(draft.currency)) return ENTERPRISE_SETUP_CURRENCY_PATH
  if (!canSubmitVatStatus(draft.vat_status, draft.vat_number ?? '')) {
    return ENTERPRISE_SETUP_VAT_PATH
  }
  return null
}

export function isEnterpriseSetupDraftComplete(draft: EnterpriseSetupDraft): boolean {
  return firstIncompleteEnterpriseSetupPath(draft) === null
}

export function vatHelpTextForCountry(countryCode: string): string {
  const code = normalizeCountryCode(countryCode)
  if (code === 'FR') {
    return 'Certaines entreprises peuvent bénéficier de la franchise en base de TVA. En cas de doute, vous pourrez modifier ce réglage plus tard.'
  }
  return 'Les règles de TVA dépendent de votre pays et de votre activité. Ce réglage pourra être modifié plus tard.'
}

export function parseEnterpriseSetupDraft(raw: unknown): EnterpriseSetupDraft {
  if (!raw || typeof raw !== 'object') return emptyEnterpriseSetupDraft()
  const source = raw as {
    company_name?: unknown
    industry?: unknown
    industry_other?: unknown
    country?: unknown
    currency?: unknown
    vat_status?: unknown
    vat_number?: unknown
  }

  let company_name = ''
  if (typeof source.company_name === 'string') {
    company_name = source.company_name.slice(0, COMPANY_NAME_MAX_LENGTH)
  }

  let industry = ''
  if (typeof source.industry === 'string' && isEnterpriseSetupIndustryId(source.industry)) {
    industry = source.industry
  }

  let industry_other: string | undefined
  if (industry === 'other' && typeof source.industry_other === 'string') {
    industry_other = source.industry_other.slice(0, INDUSTRY_OTHER_MAX_LENGTH)
  }

  let country = ''
  if (typeof source.country === 'string') {
    const normalized = normalizeCountryCode(source.country)
    if (isValidCountryCode(normalized)) {
      country = normalized
    }
  }

  let currency = ''
  if (typeof source.currency === 'string') {
    const normalized = normalizeCurrencyCode(source.currency)
    if (isValidCurrencyCode(normalized)) {
      currency = normalized
    }
  }

  let vat_status = ''
  if (typeof source.vat_status === 'string' && isEnterpriseSetupVatStatus(source.vat_status)) {
    vat_status = source.vat_status
  }

  let vat_number: string | undefined
  if (vat_status === 'vat_registered' && typeof source.vat_number === 'string') {
    const normalized = normalizeVatNumber(source.vat_number)
    if (normalized && validateVatNumber(source.vat_number) === null) {
      vat_number = normalized
    } else if (normalized) {
      // conserver une saisie partielle lisible si format douteux ? Spec: normalize; invalid chars rejected on submit
      // À la lecture, garder uniquement si valide ; sinon ignorer le numéro
      vat_number = undefined
    }
  }

  return {
    company_name,
    industry,
    country,
    currency,
    vat_status,
    ...(industry_other !== undefined ? { industry_other } : {}),
    ...(vat_number !== undefined ? { vat_number } : {}),
  }
}

export function serializeEnterpriseSetupDraft(draft: EnterpriseSetupDraft): EnterpriseSetupDraft {
  const industry =
    typeof draft.industry === 'string' && isEnterpriseSetupIndustryId(draft.industry)
      ? draft.industry
      : ''
  const country =
    typeof draft.country === 'string' && isValidCountryCode(draft.country)
      ? normalizeCountryCode(draft.country)
      : ''
  const currency =
    typeof draft.currency === 'string' && isValidCurrencyCode(draft.currency)
      ? normalizeCurrencyCode(draft.currency)
      : ''
  const vat_status =
    typeof draft.vat_status === 'string' && isEnterpriseSetupVatStatus(draft.vat_status)
      ? draft.vat_status
      : ''
  const next: EnterpriseSetupDraft = {
    company_name: String(draft.company_name ?? '').slice(0, COMPANY_NAME_MAX_LENGTH),
    industry,
    country,
    currency,
    vat_status,
  }
  if (industry === 'other') {
    next.industry_other = String(draft.industry_other ?? '').slice(0, INDUSTRY_OTHER_MAX_LENGTH)
  }
  if (vat_status === 'vat_registered') {
    const number = normalizeVatNumber(String(draft.vat_number ?? ''))
    if (number) next.vat_number = number
  }
  return next
}

export function readEnterpriseSetupDraftFromStorage(
  storage: Pick<Storage, 'getItem'> | null = typeof sessionStorage !== 'undefined'
    ? sessionStorage
    : null,
): EnterpriseSetupDraft {
  if (!storage) return emptyEnterpriseSetupDraft()
  try {
    const raw = storage.getItem(ENTERPRISE_SETUP_DRAFT_STORAGE_KEY)
    if (!raw) return emptyEnterpriseSetupDraft()
    return parseEnterpriseSetupDraft(JSON.parse(raw) as unknown)
  } catch {
    return emptyEnterpriseSetupDraft()
  }
}

export function writeEnterpriseSetupDraftToStorage(
  draft: EnterpriseSetupDraft,
  storage: Pick<Storage, 'setItem'> | null = typeof sessionStorage !== 'undefined'
    ? sessionStorage
    : null,
): void {
  if (!storage) return
  try {
    storage.setItem(
      ENTERPRISE_SETUP_DRAFT_STORAGE_KEY,
      JSON.stringify(serializeEnterpriseSetupDraft(draft)),
    )
  } catch {
    /* quota / mode privé */
  }
}

export function clearEnterpriseSetupDraftFromStorage(
  storage: Pick<Storage, 'removeItem'> | null = typeof sessionStorage !== 'undefined'
    ? sessionStorage
    : null,
): void {
  if (!storage) return
  try {
    storage.removeItem(ENTERPRISE_SETUP_DRAFT_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
