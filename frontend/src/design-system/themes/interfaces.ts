/**
 * Theme contracts — Theme Engine Foundation V1 (E1.2).
 */

import type {
  AccentGradient,
  ProductBrandingAssets,
  ProductCategoryId,
  ProductId,
  ProductIdentity,
  ProductStatus,
  ThemeId,
} from '../types'
import type { PilotTokens } from '../tokens/pilotTokens'

/** V1 product themes are light-only (no incomplete dark mode). */
export type ColorScheme = 'light' | 'dark' | 'system'

export type AppliedColorScheme = 'light'

export type ThemeBranding = ProductBrandingAssets & {
  displayName: string
  shortName: string
}

export type ProductThemeMetadata = {
  status: ProductStatus
  category: ProductCategoryId
  tagline: string
  accentGradient: AccentGradient
  resolvedFromFallback: boolean
  requestedProductId?: string
}

export type ProductTheme = {
  productId: ProductId
  themeId: ThemeId
  colorScheme: AppliedColorScheme
  tokens: PilotTokens
  branding: ThemeBranding
  metadata: ProductThemeMetadata
  /** Full product identity snapshot for consumers. */
  product: ProductIdentity
}

/** @deprecated Prefer ColorScheme / AppliedColorScheme. */
export type DesignThemeMode = 'light' | 'dark'

export type DesignTheme = {
  platform: ProductTheme
  pilot: ProductTheme
  mode: AppliedColorScheme
}

export type DesignThemeApi = {
  getTheme(): DesignTheme
  setPilot(productId: ProductId): void
  setMode(mode: DesignThemeMode): void
}

export type ResolveProductThemeOptions = {
  /** Surface hint for fallback choice when id unknown. */
  surface?: 'workspace' | 'platform'
  /** Force color scheme — V1 always resolves to light. */
  colorScheme?: ColorScheme
}

export type ThemeValidationIssue = {
  code: string
  message: string
}

export type ThemeValidationResult = {
  ok: boolean
  issues: readonly ThemeValidationIssue[]
}

export type ThemeDomAttributes = {
  'data-product': string
  'data-theme': string
  'data-color-scheme': AppliedColorScheme
}

export type BrandingAssetType = 'logo' | 'logoMark' | 'favicon' | 'icon' | 'illustrations'
