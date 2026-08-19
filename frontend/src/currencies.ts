/**
 * Devises ISO 4217 — source unique pour l’Enterprise Setup.
 * Codes stables pour le draft ; libellés FR pour l’UI.
 */

import { foldSearchText, normalizeCountryCode } from './countries'

export type IsoCurrency = {
  code: string
  name: string
  symbol: string
  /** Ordre d’affichage croissant (recommandés en tête). */
  order: number
}

export const ISO_CURRENCIES: readonly IsoCurrency[] = [
  { code: 'EUR', name: 'Euro', symbol: '€', order: 10 },
  { code: 'USD', name: 'Dollar américain', symbol: '$', order: 20 },
  { code: 'GBP', name: 'Livre sterling', symbol: '£', order: 30 },
  { code: 'CHF', name: 'Franc suisse', symbol: 'CHF', order: 40 },
  { code: 'CAD', name: 'Dollar canadien', symbol: 'CA$', order: 50 },
  { code: 'AUD', name: 'Dollar australien', symbol: 'A$', order: 60 },
  { code: 'JPY', name: 'Yen japonais', symbol: '¥', order: 70 },
  { code: 'CNY', name: 'Yuan chinois', symbol: 'CN¥', order: 80 },
  { code: 'AED', name: 'Dirham des ÉAU', symbol: 'د.إ', order: 90 },
  { code: 'MAD', name: 'Dirham marocain', symbol: 'MAD', order: 100 },
  { code: 'XOF', name: 'Franc CFA (BCEAO)', symbol: 'F CFA', order: 110 },
  { code: 'XAF', name: 'Franc CFA (BEAC)', symbol: 'FCFA', order: 120 },
] as const

const CURRENCY_BY_CODE = new Map(ISO_CURRENCIES.map((c) => [c.code, c]))

/** Mapping pays → devise recommandée (jamais imposée). */
export const COUNTRY_CURRENCY_RECOMMENDATIONS: Readonly<Record<string, string>> = {
  FR: 'EUR',
  BE: 'EUR',
  LU: 'EUR',
  DE: 'EUR',
  ES: 'EUR',
  IT: 'EUR',
  PT: 'EUR',
  NL: 'EUR',
  AT: 'EUR',
  IE: 'EUR',
  FI: 'EUR',
  GR: 'EUR',
  CH: 'CHF',
  GB: 'GBP',
  US: 'USD',
  CA: 'CAD',
  AU: 'AUD',
  JP: 'JPY',
  CN: 'CNY',
  AE: 'AED',
  MA: 'MAD',
  SN: 'XOF',
  CI: 'XOF',
  CM: 'XAF',
  GA: 'XAF',
}

export function normalizeCurrencyCode(raw: string): string {
  return String(raw || '')
    .trim()
    .toUpperCase()
}

export function isValidCurrencyCode(raw: string): boolean {
  const code = normalizeCurrencyCode(raw)
  return code.length === 3 && CURRENCY_BY_CODE.has(code)
}

export function getCurrencyByCode(raw: string): IsoCurrency | undefined {
  return CURRENCY_BY_CODE.get(normalizeCurrencyCode(raw))
}

export function formatCurrencyOption(currency: IsoCurrency): string {
  return `${currency.name} (${currency.code})`
}

export function recommendedCurrencyForCountry(countryCode: string): string | null {
  if (!countryCode) return null
  const code = normalizeCountryCode(countryCode)
  const recommended = COUNTRY_CURRENCY_RECOMMENDATIONS[code]
  if (!recommended || !isValidCurrencyCode(recommended)) return null
  return recommended
}

export function sortCurrencies(list: readonly IsoCurrency[]): IsoCurrency[] {
  return [...list].sort((a, b) => a.order - b.order || a.code.localeCompare(b.code))
}

export function filterCurrencies(
  query: string,
  source: readonly IsoCurrency[] = ISO_CURRENCIES,
): IsoCurrency[] {
  const q = foldSearchText(query)
  const sorted = sortCurrencies(source)
  if (!q) return sorted
  return sorted.filter((currency) => {
    return (
      foldSearchText(currency.code).includes(q) ||
      foldSearchText(currency.name).includes(q) ||
      foldSearchText(currency.symbol).includes(q)
    )
  })
}
