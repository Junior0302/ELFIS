/**
 * Pays ISO 3166-1 alpha-2 — source unique pour l’Enterprise Setup.
 * Libellés FR pour l’UI ; codes stables pour le draft.
 */

export type IsoCountry = {
  code: string
  label: string
}

/** Pays mis en avant (cartes) — ordre d’affichage. */
export const FREQUENT_COUNTRY_CODES = [
  'FR',
  'BE',
  'LU',
  'CH',
  'DE',
  'ES',
  'IT',
  'PT',
  'NL',
  'GB',
] as const

/**
 * Catalogue ISO centralisé (sous-ensemble produit utile + pays fréquents).
 * Extensible sans toucher les pages.
 */
export const ISO_COUNTRIES: readonly IsoCountry[] = [
  { code: 'AF', label: 'Afghanistan' },
  { code: 'ZA', label: 'Afrique du Sud' },
  { code: 'AL', label: 'Albanie' },
  { code: 'DZ', label: 'Algérie' },
  { code: 'DE', label: 'Allemagne' },
  { code: 'AD', label: 'Andorre' },
  { code: 'AO', label: 'Angola' },
  { code: 'SA', label: 'Arabie saoudite' },
  { code: 'AR', label: 'Argentine' },
  { code: 'AM', label: 'Arménie' },
  { code: 'AU', label: 'Australie' },
  { code: 'AT', label: 'Autriche' },
  { code: 'AZ', label: 'Azerbaïdjan' },
  { code: 'BH', label: 'Bahreïn' },
  { code: 'BD', label: 'Bangladesh' },
  { code: 'BE', label: 'Belgique' },
  { code: 'BJ', label: 'Bénin' },
  { code: 'BY', label: 'Biélorussie' },
  { code: 'BO', label: 'Bolivie' },
  { code: 'BA', label: 'Bosnie-Herzégovine' },
  { code: 'BW', label: 'Botswana' },
  { code: 'BR', label: 'Brésil' },
  { code: 'BG', label: 'Bulgarie' },
  { code: 'BF', label: 'Burkina Faso' },
  { code: 'BI', label: 'Burundi' },
  { code: 'KH', label: 'Cambodge' },
  { code: 'CM', label: 'Cameroun' },
  { code: 'CA', label: 'Canada' },
  { code: 'CV', label: 'Cap-Vert' },
  { code: 'CL', label: 'Chili' },
  { code: 'CN', label: 'Chine' },
  { code: 'CY', label: 'Chypre' },
  { code: 'CO', label: 'Colombie' },
  { code: 'KM', label: 'Comores' },
  { code: 'CG', label: 'Congo' },
  { code: 'CD', label: 'Congo (RDC)' },
  { code: 'KR', label: 'Corée du Sud' },
  { code: 'CR', label: 'Costa Rica' },
  { code: 'CI', label: 'Côte d’Ivoire' },
  { code: 'HR', label: 'Croatie' },
  { code: 'CU', label: 'Cuba' },
  { code: 'DK', label: 'Danemark' },
  { code: 'DJ', label: 'Djibouti' },
  { code: 'EG', label: 'Égypte' },
  { code: 'AE', label: 'Émirats arabes unis' },
  { code: 'EC', label: 'Équateur' },
  { code: 'ER', label: 'Érythrée' },
  { code: 'ES', label: 'Espagne' },
  { code: 'EE', label: 'Estonie' },
  { code: 'SZ', label: 'Eswatini' },
  { code: 'US', label: 'États-Unis' },
  { code: 'ET', label: 'Éthiopie' },
  { code: 'FI', label: 'Finlande' },
  { code: 'FR', label: 'France' },
  { code: 'GA', label: 'Gabon' },
  { code: 'GM', label: 'Gambie' },
  { code: 'GE', label: 'Géorgie' },
  { code: 'GH', label: 'Ghana' },
  { code: 'GR', label: 'Grèce' },
  { code: 'GT', label: 'Guatemala' },
  { code: 'GN', label: 'Guinée' },
  { code: 'GQ', label: 'Guinée équatoriale' },
  { code: 'GW', label: 'Guinée-Bissau' },
  { code: 'HT', label: 'Haïti' },
  { code: 'HN', label: 'Honduras' },
  { code: 'HU', label: 'Hongrie' },
  { code: 'IN', label: 'Inde' },
  { code: 'ID', label: 'Indonésie' },
  { code: 'IQ', label: 'Irak' },
  { code: 'IE', label: 'Irlande' },
  { code: 'IS', label: 'Islande' },
  { code: 'IL', label: 'Israël' },
  { code: 'IT', label: 'Italie' },
  { code: 'JP', label: 'Japon' },
  { code: 'JO', label: 'Jordanie' },
  { code: 'KZ', label: 'Kazakhstan' },
  { code: 'KE', label: 'Kenya' },
  { code: 'KW', label: 'Koweït' },
  { code: 'LA', label: 'Laos' },
  { code: 'LV', label: 'Lettonie' },
  { code: 'LB', label: 'Liban' },
  { code: 'LR', label: 'Libéria' },
  { code: 'LY', label: 'Libye' },
  { code: 'LI', label: 'Liechtenstein' },
  { code: 'LT', label: 'Lituanie' },
  { code: 'LU', label: 'Luxembourg' },
  { code: 'MG', label: 'Madagascar' },
  { code: 'MY', label: 'Malaisie' },
  { code: 'ML', label: 'Mali' },
  { code: 'MT', label: 'Malte' },
  { code: 'MA', label: 'Maroc' },
  { code: 'MU', label: 'Maurice' },
  { code: 'MR', label: 'Mauritanie' },
  { code: 'MX', label: 'Mexique' },
  { code: 'MD', label: 'Moldavie' },
  { code: 'MC', label: 'Monaco' },
  { code: 'MN', label: 'Mongolie' },
  { code: 'ME', label: 'Monténégro' },
  { code: 'MZ', label: 'Mozambique' },
  { code: 'NA', label: 'Namibie' },
  { code: 'NP', label: 'Népal' },
  { code: 'NI', label: 'Nicaragua' },
  { code: 'NE', label: 'Niger' },
  { code: 'NG', label: 'Nigéria' },
  { code: 'NO', label: 'Norvège' },
  { code: 'NZ', label: 'Nouvelle-Zélande' },
  { code: 'OM', label: 'Oman' },
  { code: 'UG', label: 'Ouganda' },
  { code: 'UZ', label: 'Ouzbékistan' },
  { code: 'PK', label: 'Pakistan' },
  { code: 'PA', label: 'Panama' },
  { code: 'PY', label: 'Paraguay' },
  { code: 'NL', label: 'Pays-Bas' },
  { code: 'PE', label: 'Pérou' },
  { code: 'PH', label: 'Philippines' },
  { code: 'PL', label: 'Pologne' },
  { code: 'PT', label: 'Portugal' },
  { code: 'QA', label: 'Qatar' },
  { code: 'CF', label: 'République centrafricaine' },
  { code: 'DO', label: 'République dominicaine' },
  { code: 'CZ', label: 'République tchèque' },
  { code: 'RO', label: 'Roumanie' },
  { code: 'GB', label: 'Royaume-Uni' },
  { code: 'RU', label: 'Russie' },
  { code: 'RW', label: 'Rwanda' },
  { code: 'SN', label: 'Sénégal' },
  { code: 'RS', label: 'Serbie' },
  { code: 'SC', label: 'Seychelles' },
  { code: 'SL', label: 'Sierra Leone' },
  { code: 'SG', label: 'Singapour' },
  { code: 'SK', label: 'Slovaquie' },
  { code: 'SI', label: 'Slovénie' },
  { code: 'SO', label: 'Somalie' },
  { code: 'SD', label: 'Soudan' },
  { code: 'LK', label: 'Sri Lanka' },
  { code: 'SE', label: 'Suède' },
  { code: 'CH', label: 'Suisse' },
  { code: 'SR', label: 'Suriname' },
  { code: 'SY', label: 'Syrie' },
  { code: 'TJ', label: 'Tadjikistan' },
  { code: 'TZ', label: 'Tanzanie' },
  { code: 'TD', label: 'Tchad' },
  { code: 'TH', label: 'Thaïlande' },
  { code: 'TL', label: 'Timor oriental' },
  { code: 'TG', label: 'Togo' },
  { code: 'TN', label: 'Tunisie' },
  { code: 'TM', label: 'Turkménistan' },
  { code: 'TR', label: 'Turquie' },
  { code: 'UA', label: 'Ukraine' },
  { code: 'UY', label: 'Uruguay' },
  { code: 'VU', label: 'Vanuatu' },
  { code: 'VE', label: 'Venezuela' },
  { code: 'VN', label: 'Viêt Nam' },
  { code: 'YE', label: 'Yémen' },
  { code: 'ZM', label: 'Zambie' },
  { code: 'ZW', label: 'Zimbabwe' },
] as const

const COUNTRY_BY_CODE = new Map(ISO_COUNTRIES.map((c) => [c.code, c]))

export function foldSearchText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
}

export function normalizeCountryCode(raw: string): string {
  return String(raw || '')
    .trim()
    .toUpperCase()
}

export function isValidCountryCode(raw: string): boolean {
  const code = normalizeCountryCode(raw)
  return code.length === 2 && COUNTRY_BY_CODE.has(code)
}

export function getCountryByCode(raw: string): IsoCountry | undefined {
  return COUNTRY_BY_CODE.get(normalizeCountryCode(raw))
}

export function getCountryLabel(raw: string): string {
  return getCountryByCode(raw)?.label ?? ''
}

export function getFrequentCountries(): IsoCountry[] {
  return FREQUENT_COUNTRY_CODES.map((code) => COUNTRY_BY_CODE.get(code)).filter(
    (item): item is IsoCountry => Boolean(item),
  )
}

export function filterCountries(query: string, source: readonly IsoCountry[] = ISO_COUNTRIES): IsoCountry[] {
  const q = foldSearchText(query)
  if (!q) return [...source].sort((a, b) => a.label.localeCompare(b.label, 'fr'))
  return source
    .filter((country) => {
      const label = foldSearchText(country.label)
      const code = foldSearchText(country.code)
      return label.includes(q) || code.includes(q)
    })
    .sort((a, b) => a.label.localeCompare(b.label, 'fr'))
}

/**
 * Liste combobox : sans recherche → fréquents puis le reste (scroll UI) ;
 * avec recherche → résultats filtrés.
 */
export function countriesForCombobox(query: string): IsoCountry[] {
  const q = foldSearchText(query)
  if (!q) {
    const frequent = getFrequentCountries()
    const frequentCodes = new Set(frequent.map((country) => country.code))
    const rest = [...ISO_COUNTRIES]
      .filter((country) => !frequentCodes.has(country.code))
      .sort((a, b) => a.label.localeCompare(b.label, 'fr'))
    return [...frequent, ...rest]
  }
  return filterCountries(query)
}
