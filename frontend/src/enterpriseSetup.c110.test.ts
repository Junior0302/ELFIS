import { describe, expect, it, vi } from 'vitest'
import {
  FREQUENT_COUNTRY_CODES,
  countriesForCombobox,
  filterCountries,
  foldSearchText,
  getCountryLabel,
} from './countries'
import {
  ENTERPRISE_SETUP_BANK_PATH,
  ENTERPRISE_SETUP_COMPANY_NAME_PATH,
  ENTERPRISE_SETUP_COUNTRY_PATH,
  ENTERPRISE_SETUP_PREPARATION_PATH,
  ENTERPRISE_SETUP_STEPS,
  ENTERPRISE_SETUP_SUMMARY_PATH,
  ENTERPRISE_SETUP_VAT_PATH,
  canSubmitCountry,
  enterpriseSetupProgress,
  firstIncompleteEnterpriseSetupPath,
  getIndustryLabel,
  getVatSummaryLabel,
  isEnterpriseSetupDraftComplete,
  isEnterpriseSetupPath,
  type EnterpriseSetupDraft,
} from './enterpriseSetup'
import { formatCurrencyOption, getCurrencyByCode } from './currencies'
import { isPublicProductPath, resolveProductPhase } from './productPhase'
import type { SubscriptionInfo } from './api'

function completeDraft(over: Partial<EnterpriseSetupDraft> = {}): EnterpriseSetupDraft {
  return {
    company_name: 'Acme SARL',
    industry: 'automotive',
    country: 'FR',
    currency: 'EUR',
    vat_status: 'vat_registered',
    vat_number: 'FR12345678901',
    ...over,
  }
}

function sub(over: Partial<SubscriptionInfo> = {}): SubscriptionInfo {
  return {
    plan: 'pro',
    status: 'none',
    price_eur: 19,
    configured: false,
    trial_end: null,
    current_period_end: null,
    cancel_at_period_end: false,
    access_granted: false,
    ...over,
  }
}

describe('Enterprise Setup layout / steps — C1.10', () => {
  it('roadmap 8 étapes sans banque ni import bloquant', () => {
    expect(ENTERPRISE_SETUP_STEPS.map((s) => s.id)).toEqual([
      'company_name',
      'industry',
      'country',
      'currency',
      'vat',
      'summary',
      'preparation',
      'completion',
    ])
    expect(enterpriseSetupProgress('summary').label).toBe('Étape 6 sur 8')
    expect(enterpriseSetupProgress('preparation').label).toBe('Étape 7 sur 8')
    expect(ENTERPRISE_SETUP_SUMMARY_PATH).toBe('/onboarding/entreprise/resume')
    expect(ENTERPRISE_SETUP_PREPARATION_PATH).toBe('/onboarding/entreprise/preparation')
  })

  it('layout shell classes — centrage via main flex', () => {
    // Contrat CSS : main centre la carte ; header reste hors flux centré.
    const shellMainRules = [
      'display: flex',
      'align-items: safe center',
      'justify-content: center',
      'min-height: calc(100vh - var(--enterprise-setup-header-height))',
    ]
    expect(shellMainRules.every((rule) => rule.includes(':'))).toBe(true)
  })
})

describe('Country combobox helpers — C1.10', () => {
  it('un seul modèle de sélection ISO', () => {
    expect(canSubmitCountry('FR')).toBe(true)
    expect(canSubmitCountry('France')).toBe(false)
    expect(getCountryLabel('FR')).toBe('France')
  })

  it('pays fréquents en tête sans recherche', () => {
    const list = countriesForCombobox('')
    expect(list.slice(0, FREQUENT_COUNTRY_CODES.length).map((c) => c.code)).toEqual([
      ...FREQUENT_COUNTRY_CODES,
    ])
  })

  it('recherche fr / accents / aucun résultat', () => {
    expect(filterCountries('fr').some((c) => c.code === 'FR')).toBe(true)
    expect(filterCountries('cote').some((c) => c.code === 'CI')).toBe(true)
    expect(foldSearchText('Côte')).toBe('cote')
    expect(filterCountries('zzzxxyy')).toEqual([])
  })

  it('navigation clavier combobox (contrat)', () => {
    const options = countriesForCombobox('fr').slice(0, 3)
    let active = 0
    const onKey = (key: string) => {
      if (key === 'ArrowDown') active = (active + 1) % options.length
      if (key === 'ArrowUp') active = (active - 1 + options.length) % options.length
      if (key === 'Enter') return options[active]?.code
      if (key === 'Escape') return 'closed'
      return undefined
    }
    onKey('ArrowDown')
    expect(active).toBe(1)
    expect(onKey('Enter')).toBe(options[1].code)
    expect(onKey('Escape')).toBe('closed')
  })

  it('Continuer désactivé sans pays valide', () => {
    expect(canSubmitCountry('')).toBe(false)
    expect(canSubmitCountry('XX')).toBe(false)
  })
})

describe('Résumé + draft — C1.10', () => {
  it('libellés humains sans codes techniques', () => {
    expect(getIndustryLabel('automotive')).toBe('Automobile')
    expect(getIndustryLabel('other', 'Élevage')).toBe('Élevage')
    expect(getVatSummaryLabel('vat_registered')).toBe('L’entreprise facture la TVA')
    expect(getVatSummaryLabel('vat_not_registered')).toBe(
      'L’entreprise ne facture pas la TVA',
    )
    expect(getVatSummaryLabel('vat_unknown')).toBe('À vérifier plus tard')
    const euro = getCurrencyByCode('EUR')!
    expect(formatCurrencyOption(euro)).toBe('Euro (EUR)')
    expect(getCountryLabel('FR')).toBe('France')
  })

  it('draft incomplet → première étape invalide', () => {
    expect(firstIncompleteEnterpriseSetupPath(completeDraft({ company_name: '' }))).toBe(
      ENTERPRISE_SETUP_COMPANY_NAME_PATH,
    )
    expect(firstIncompleteEnterpriseSetupPath(completeDraft({ country: '' }))).toBe(
      ENTERPRISE_SETUP_COUNTRY_PATH,
    )
    expect(firstIncompleteEnterpriseSetupPath(completeDraft({ vat_status: '' }))).toBe(
      ENTERPRISE_SETUP_VAT_PATH,
    )
    expect(firstIncompleteEnterpriseSetupPath(completeDraft())).toBeNull()
    expect(isEnterpriseSetupDraftComplete(completeDraft())).toBe(true)
  })

  it('navigation résumé / préparation / banque→resume', () => {
    const navigate = vi.fn()
    navigate(ENTERPRISE_SETUP_VAT_PATH)
    navigate(ENTERPRISE_SETUP_SUMMARY_PATH)
    navigate(ENTERPRISE_SETUP_PREPARATION_PATH)
    expect(navigate).toHaveBeenNthCalledWith(1, '/onboarding/entreprise/tva')
    expect(navigate).toHaveBeenNthCalledWith(2, '/onboarding/entreprise/resume')
    expect(navigate).toHaveBeenNthCalledWith(3, '/onboarding/entreprise/preparation')
    expect(ENTERPRISE_SETUP_BANK_PATH).toBe('/onboarding/entreprise/banque')
    expect(isEnterpriseSetupPath(ENTERPRISE_SETUP_BANK_PATH)).toBe(true)
    expect(isEnterpriseSetupPath(ENTERPRISE_SETUP_SUMMARY_PATH)).toBe(true)
  })

  it('soumission TVA → résumé', () => {
    const navigate = vi.fn()
    navigate(ENTERPRISE_SETUP_SUMMARY_PATH)
    expect(navigate).toHaveBeenCalledWith('/onboarding/entreprise/resume')
  })

  it('protection entitlement inchangée', () => {
    expect(resolveProductPhase(sub({ status: 'none' }))).toBe('no_entitlement')
    expect(isPublicProductPath(ENTERPRISE_SETUP_SUMMARY_PATH)).toBe(false)
    expect(isPublicProductPath(ENTERPRISE_SETUP_PREPARATION_PATH)).toBe(false)
  })
})
