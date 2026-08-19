import { describe, expect, it, vi } from 'vitest'
import type { SubscriptionInfo } from './api'
import {
  ENTERPRISE_SETUP_BANK_PATH,
  ENTERPRISE_SETUP_CURRENCY_PATH,
  ENTERPRISE_SETUP_DRAFT_STORAGE_KEY,
  ENTERPRISE_SETUP_PATH,
  ENTERPRISE_SETUP_STEPS,
  ENTERPRISE_SETUP_SUMMARY_PATH,
  ENTERPRISE_SETUP_VAT_PATH,
  ENTERPRISE_SETUP_VAT_STATUSES,
  POST_ENTITLEMENT_SETUP_PATH,
  canSubmitVatStatus,
  enterpriseSetupProgress,
  isEnterpriseSetupPath,
  normalizeVatNumber,
  parseEnterpriseSetupDraft,
  readEnterpriseSetupDraftFromStorage,
  validateVatNumber,
  validateVatStatus,
  vatHelpTextForCountry,
  writeEnterpriseSetupDraftToStorage,
} from './enterpriseSetup'
import { isEntitledAfterRefresh } from './devTrial'
import { isPublicProductPath, resolveProductPhase } from './productPhase'

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

function memoryStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial))
  return {
    getItem: (key: string) => (map.has(key) ? map.get(key)! : null),
    setItem: (key: string, value: string) => {
      map.set(key, value)
    },
    raw: map,
  }
}

describe('Enterprise Setup — C1.9 VAT', () => {
  it('1. page étape 5 : progression, options, navigation', () => {
    expect(enterpriseSetupProgress('vat').label).toBe('Étape 5 sur 8')
    expect(enterpriseSetupProgress('vat').current).toBe(5)
    expect(ENTERPRISE_SETUP_VAT_STATUSES.map((s) => s.id)).toEqual([
      'vat_registered',
      'vat_not_registered',
      'vat_unknown',
    ])
    expect(ENTERPRISE_SETUP_CURRENCY_PATH).toBe('/onboarding/entreprise/devise')
    expect(ENTERPRISE_SETUP_SUMMARY_PATH).toBe('/onboarding/entreprise/resume')
    expect(ENTERPRISE_SETUP_BANK_PATH).toBe('/onboarding/entreprise/banque')
  })

  it('2. aucun statut → Continuer refusé', () => {
    expect(canSubmitVatStatus('')).toBe(false)
    expect(validateVatStatus('')).toBe('Indiquez si votre entreprise facture la TVA.')
  })

  it('3–5. options principales', () => {
    expect(canSubmitVatStatus('vat_registered')).toBe(true)
    expect(canSubmitVatStatus('vat_not_registered')).toBe(true)
    expect(canSubmitVatStatus('vat_unknown')).toBe(true)
  })

  it('6. vat_registered → autre statut : vat_number retiré', () => {
    const storage = memoryStorage()
    writeEnterpriseSetupDraftToStorage(
      {
        company_name: 'Acme',
        industry: 'services',
        country: 'FR',
        currency: 'EUR',
        vat_status: 'vat_registered',
        vat_number: 'FR12345678901',
      },
      storage,
    )
    writeEnterpriseSetupDraftToStorage(
      {
        company_name: 'Acme',
        industry: 'services',
        country: 'FR',
        currency: 'EUR',
        vat_status: 'vat_not_registered',
        vat_number: 'FR12345678901',
      },
      storage,
    )
    const draft = readEnterpriseSetupDraftFromStorage(storage)
    expect(draft.vat_status).toBe('vat_not_registered')
    expect(draft.vat_number).toBeUndefined()
  })

  it('7. numéro vide avec vat_registered → OK', () => {
    expect(canSubmitVatStatus('vat_registered', '')).toBe(true)
    expect(validateVatNumber('')).toBeNull()
  })

  it('8. numéro valide → trim / majuscules / espaces', () => {
    expect(normalizeVatNumber('  fr 12 345 678 901  ')).toBe('FR12345678901')
    expect(validateVatNumber('fr 12 345 678 901')).toBeNull()
  })

  it('9–10. numéro invalide / trop long', () => {
    expect(validateVatNumber('FR-123')).toBe('Vérifiez le format du numéro de TVA.')
    expect(canSubmitVatStatus('vat_registered', 'FR-123')).toBe(false)
    expect(validateVatNumber('A'.repeat(33))).toBe('Vérifiez le format du numéro de TVA.')
  })

  it('11–12. Retour devise / Continuer résumé', () => {
    const navigate = vi.fn()
    navigate(ENTERPRISE_SETUP_CURRENCY_PATH)
    navigate(ENTERPRISE_SETUP_SUMMARY_PATH)
    expect(navigate).toHaveBeenNthCalledWith(1, '/onboarding/entreprise/devise')
    expect(navigate).toHaveBeenNthCalledWith(2, '/onboarding/entreprise/resume')
  })

  it('13. restauration sélection', () => {
    const storage = memoryStorage()
    writeEnterpriseSetupDraftToStorage(
      {
        company_name: 'Acme',
        industry: 'commerce',
        country: 'BE',
        currency: 'EUR',
        vat_status: 'vat_unknown',
      },
      storage,
    )
    expect(readEnterpriseSetupDraftFromStorage(storage).vat_status).toBe('vat_unknown')
  })

  it('14–15. draft invalide / vat_number nettoyé', () => {
    const invalidStatus = parseEnterpriseSetupDraft({
      company_name: 'Acme',
      industry: 'commerce',
      country: 'FR',
      currency: 'EUR',
      vat_status: 'franchise_base',
      vat_number: 'FR123',
    })
    expect(invalidStatus.vat_status).toBe('')
    expect(invalidStatus.vat_number).toBeUndefined()

    const cleaned = parseEnterpriseSetupDraft({
      company_name: 'Acme',
      industry: 'commerce',
      country: 'FR',
      currency: 'EUR',
      vat_status: 'vat_not_registered',
      vat_number: 'FR12345678901',
    })
    expect(cleaned.vat_status).toBe('vat_not_registered')
    expect(cleaned.vat_number).toBeUndefined()
  })

  it('16–17. aide contextuelle FR / générique', () => {
    expect(vatHelpTextForCountry('FR')).toMatch(/franchise en base/i)
    expect(vatHelpTextForCountry('FR')).not.toMatch(/vous êtes éligible/i)
    expect(vatHelpTextForCountry('DE')).toMatch(/dépendent de votre pays/i)
  })

  it('18. clavier Entrée / Espace', () => {
    let selected = ''
    const onKey = (key: string, id: string) => {
      if (key === 'Enter' || key === ' ') selected = id
    }
    onKey('Enter', 'vat_registered')
    expect(selected).toBe('vat_registered')
    onKey(' ', 'vat_unknown')
    expect(selected).toBe('vat_unknown')
  })

  it('19. progression depuis ENTERPRISE_SETUP_STEPS', () => {
    expect(enterpriseSetupProgress('vat').current).toBe(
      ENTERPRISE_SETUP_STEPS.findIndex((s) => s.id === 'vat') + 1,
    )
  })

  it('20. sans entitlement → protection inchangée', () => {
    expect(resolveProductPhase(sub({ status: 'none' }))).toBe('no_entitlement')
    expect(isPublicProductPath(ENTERPRISE_SETUP_VAT_PATH)).toBe(false)
    expect(isPublicProductPath(ENTERPRISE_SETUP_BANK_PATH)).toBe(false)
    expect(isEnterpriseSetupPath(ENTERPRISE_SETUP_BANK_PATH)).toBe(true)
  })

  it('soumission vat → résumé (un seul appel)', () => {
    const navigate = vi.fn()
    const persistDraft = vi.fn()
    let submitting = false
    const onSubmit = () => {
      if (!canSubmitVatStatus('vat_registered', 'FR123') || submitting) return
      submitting = true
      persistDraft({
        company_name: 'Acme',
        industry: 'commerce',
        country: 'FR',
        currency: 'EUR',
        vat_status: 'vat_registered',
        vat_number: normalizeVatNumber('FR123'),
      })
      navigate(ENTERPRISE_SETUP_SUMMARY_PATH)
    }
    onSubmit()
    onSubmit()
    expect(persistDraft).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/onboarding/entreprise/resume')
  })

  it('draft JSON corrompu → vide sans crash', () => {
    const storage = memoryStorage({
      [ENTERPRISE_SETUP_DRAFT_STORAGE_KEY]: '{not-json',
    })
    expect(readEnterpriseSetupDraftFromStorage(storage)).toEqual({
      company_name: '',
      industry: '',
      country: '',
      currency: '',
      vat_status: '',
    })
  })

  it('entitled + post-activation', () => {
    const entitled = sub({
      status: 'trialing',
      access_granted: true,
      trial_end: '2099-01-01T00:00:00Z',
    })
    expect(resolveProductPhase(entitled)).toBe('entitled')
    expect(isEntitledAfterRefresh(entitled)).toBe(true)
    expect(POST_ENTITLEMENT_SETUP_PATH).toBe(ENTERPRISE_SETUP_PATH)
  })
})
