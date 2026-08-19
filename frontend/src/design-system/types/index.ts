/** Types Design System ELFIS — Brand Foundation + Product Identity V1. */

export type ProductStatus =
  | 'active'
  | 'beta'
  | 'coming_soon'
  | 'internal'
  | 'archived'

export type ProductId =
  | 'elfis-core'
  | 'comptapilot'
  | 'salespilot'
  | 'docpilot'
  | 'hrpilot'
  | 'legalpilot'
  | 'inventorypilot'
  | 'marketingpilot'
  | 'projectpilot'
  | 'supportpilot'

/** Theme identifier — 1:1 with ProductId until multi-theme-per-product exists. */
export type ThemeId = ProductId

export type ProductFamily =
  | 'platform'
  | 'pilot_app'
  | 'shared_service'
  | 'future_product'

export type ProductCategoryId =
  | 'platform'
  | 'finance'
  | 'sales'
  | 'documents'
  | 'people'
  | 'legal'
  | 'operations'
  | 'marketing'
  | 'projects'
  | 'support'

export type PricingModel =
  | 'standalone'
  | 'bundle'
  | 'standalone_and_bundle'
  | 'included'
  | 'not_available'

export type IllustrationStyle =
  | 'platform_minimal'
  | 'financial_data'
  | 'sales_pipeline'
  | 'document_intelligence'
  | 'people_operations'
  | 'legal_precision'
  | 'inventory_flow'
  | 'marketing_growth'
  | 'project_collaboration'
  | 'customer_support'

export type ChartPalette = readonly [
  string,
  string,
  string,
  string,
  string,
  string,
  string,
  string,
]

export type ProductColors = {
  primaryColor: string
  secondaryColor: string
  accentColor: string
  chartPalette: ChartPalette
}

export type AccentGradient = {
  from: string
  to: string
}

export type ProductBrandingAssets = {
  /** Relative public path — placeholder until final art. */
  icon: string
  logo: string
  logoMark: string
  favicon: string
  illustrations: string
}

export type ProductCategory = {
  id: ProductCategoryId
  label: string
  description: string
  iconKey: string
  order: number
  status?: ProductStatus
}

/** Optional controlled bag — avoid free-form sprawl. */
export type ProductMetadata = {
  readonly ownerTeam?: string
  readonly notes?: string
}

/**
 * Official product identity for an ELFIS application.
 * Single source of truth consumed by future launcher, marketing, nav, billing.
 */
export type ProductIdentity = {
  id: ProductId
  slug: string
  displayName: string
  shortName: string
  productFamily: ProductFamily
  category: ProductCategoryId
  tagline: string
  shortDescription: string
  longDescription?: string
  status: ProductStatus
  themeId: ThemeId
  iconKey: string
  logo: string
  logoMark: string
  favicon: string
  accentGradient: AccentGradient
  marketingColor: string
  illustrationStyle: IllustrationStyle
  websitePath: string
  documentationPath: string
  supportEmail?: string
  launchOrder: number
  availableInLauncher: boolean
  availableForSubscription: boolean
  standaloneEligible: boolean
  bundleEligible: boolean
  defaultBundleIds: readonly string[]
  pricingModel: PricingModel
  colors: ProductColors
  branding: ProductBrandingAssets
  featureFlags?: Readonly<Record<string, boolean>>
  metadata?: ProductMetadata
  /** Up to 3 capability labels for launcher / home surfaces. */
  capabilities?: readonly string[]
  /** Featured as full coming-soon card in App Launcher. */
  featuredInLauncher?: boolean
  /** Optional launcher-only description override (falls back to shortDescription). */
  launcherDescription?: string
}

/**
 * Alias historique E1.1 — préférer `ProductIdentity`.
 */
export type ProductDefinition = ProductIdentity

/** Token types live in tokens/pilotTokens.ts (E1.2 semantic PilotTokens). */

export type RegistryValidationIssue = {
  code: string
  message: string
  productId?: ProductId
}

export type RegistryValidationResult = {
  ok: boolean
  issues: readonly RegistryValidationIssue[]
}
