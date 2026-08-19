import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  emptyEnterpriseSetupDraft,
  isEnterpriseSetupVatStatus,
  normalizeVatNumber,
  readEnterpriseSetupDraftFromStorage,
  writeEnterpriseSetupDraftToStorage,
  type EnterpriseSetupDraft,
  type EnterpriseSetupIndustryId,
  type EnterpriseSetupVatStatus,
} from './enterpriseSetup'
import { normalizeCountryCode } from './countries'
import { normalizeCurrencyCode } from './currencies'

type EnterpriseSetupContextValue = {
  draft: EnterpriseSetupDraft
  setCompanyName: (value: string) => void
  setIndustry: (industry: EnterpriseSetupIndustryId | '', industryOther?: string) => void
  setCountry: (countryCode: string) => void
  setCurrency: (currencyCode: string) => void
  setVatStatus: (status: EnterpriseSetupVatStatus | '', vatNumber?: string) => void
  persistDraft: (next?: EnterpriseSetupDraft) => void
}

const EnterpriseSetupContext = createContext<EnterpriseSetupContextValue | null>(null)

export function EnterpriseSetupProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<EnterpriseSetupDraft>(() =>
    readEnterpriseSetupDraftFromStorage(),
  )

  const setCompanyName = useCallback((value: string) => {
    setDraft((prev) => {
      const next = { ...prev, company_name: value }
      writeEnterpriseSetupDraftToStorage(next)
      return next
    })
  }, [])

  const setIndustry = useCallback(
    (industry: EnterpriseSetupIndustryId | '', industryOther?: string) => {
      setDraft((prev) => {
        const next: EnterpriseSetupDraft = {
          ...prev,
          industry,
        }
        if (industry === 'other') {
          next.industry_other = industryOther ?? prev.industry_other ?? ''
        } else {
          delete next.industry_other
        }
        writeEnterpriseSetupDraftToStorage(next)
        return next
      })
    },
    [],
  )

  const setCountry = useCallback((countryCode: string) => {
    setDraft((prev) => {
      const next = {
        ...prev,
        country: countryCode ? normalizeCountryCode(countryCode) : '',
      }
      writeEnterpriseSetupDraftToStorage(next)
      return next
    })
  }, [])

  const setCurrency = useCallback((currencyCode: string) => {
    setDraft((prev) => {
      const next = {
        ...prev,
        currency: currencyCode ? normalizeCurrencyCode(currencyCode) : '',
      }
      writeEnterpriseSetupDraftToStorage(next)
      return next
    })
  }, [])

  const setVatStatus = useCallback((status: EnterpriseSetupVatStatus | '', vatNumber?: string) => {
    setDraft((prev) => {
      const next: EnterpriseSetupDraft = {
        ...prev,
        vat_status: status && isEnterpriseSetupVatStatus(status) ? status : '',
      }
      if (status === 'vat_registered') {
        next.vat_number =
          vatNumber !== undefined
            ? normalizeVatNumber(vatNumber)
            : normalizeVatNumber(prev.vat_number ?? '')
        if (!next.vat_number) delete next.vat_number
      } else {
        delete next.vat_number
      }
      writeEnterpriseSetupDraftToStorage(next)
      return next
    })
  }, [])

  const persistDraft = useCallback((next?: EnterpriseSetupDraft) => {
    setDraft((prev) => {
      const value = next ?? prev
      writeEnterpriseSetupDraftToStorage(value)
      return value
    })
  }, [])

  const value = useMemo(
    () => ({
      draft,
      setCompanyName,
      setIndustry,
      setCountry,
      setCurrency,
      setVatStatus,
      persistDraft,
    }),
    [draft, setCompanyName, setIndustry, setCountry, setCurrency, setVatStatus, persistDraft],
  )

  return (
    <EnterpriseSetupContext.Provider value={value}>{children}</EnterpriseSetupContext.Provider>
  )
}

export function useEnterpriseSetupDraft() {
  const ctx = useContext(EnterpriseSetupContext)
  if (!ctx) {
    throw new Error('useEnterpriseSetupDraft doit être utilisé dans EnterpriseSetupProvider')
  }
  return ctx
}

export { emptyEnterpriseSetupDraft }
