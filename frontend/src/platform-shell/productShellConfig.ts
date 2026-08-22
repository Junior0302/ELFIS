import type { ProductId } from '../design-system'

/** Contrat produit → Platform Shell (pas de if produit dans le Shell). */
export type ProductShellChromeOptions = {
  showLauncher: boolean
  showSearch: boolean
  showNotifications: boolean
  showOrganizationSwitcher: boolean
  /** Indicateur Pilot actif — masqué sur Home (lockup ELFIS suffit). */
  showProductIndicator: boolean
}

export type ProductShellConfiguration = {
  productId: ProductId
  homeRoute: string
  mobileNavigationLabel: string
  /** Accent porté par tokens --pilot-* (thème route) */
  chrome: ProductShellChromeOptions
}

export const DEFAULT_SHELL_CHROME: ProductShellChromeOptions = {
  showLauncher: true,
  showSearch: true,
  showNotifications: true,
  showOrganizationSwitcher: true,
  showProductIndicator: true,
}

export const COMPTAPILOT_SHELL_CONFIG: ProductShellConfiguration = {
  productId: 'comptapilot',
  homeRoute: '/dashboard',
  mobileNavigationLabel: 'Navigation Finance',
  chrome: { ...DEFAULT_SHELL_CHROME },
}

export const SALESPILOT_SHELL_CONFIG: ProductShellConfiguration = {
  productId: 'salespilot',
  homeRoute: '/sales',
  mobileNavigationLabel: 'Navigation Commercial',
  chrome: { ...DEFAULT_SHELL_CHROME },
}

export const ELFIS_HOME_SHELL_CONFIG: ProductShellConfiguration = {
  productId: 'elfis-core',
  homeRoute: '/home',
  mobileNavigationLabel: 'Navigation ELFIS',
  chrome: {
    ...DEFAULT_SHELL_CHROME,
    showProductIndicator: false,
  },
}

const REGISTRY: Record<string, ProductShellConfiguration> = {
  comptapilot: COMPTAPILOT_SHELL_CONFIG,
  salespilot: SALESPILOT_SHELL_CONFIG,
  'elfis-core': ELFIS_HOME_SHELL_CONFIG,
}

export function getProductShellConfiguration(productId: ProductId): ProductShellConfiguration {
  return REGISTRY[productId] ?? {
    productId,
    homeRoute: '/home',
    mobileNavigationLabel: 'Navigation',
    chrome: { ...DEFAULT_SHELL_CHROME },
  }
}

export function withChromeOverrides(
  config: ProductShellConfiguration,
  overrides: Partial<ProductShellChromeOptions>,
): ProductShellConfiguration {
  return {
    ...config,
    chrome: { ...config.chrome, ...overrides },
  }
}
