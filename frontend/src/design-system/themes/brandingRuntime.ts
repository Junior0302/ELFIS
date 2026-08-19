/**
 * Branding helpers for runtime consumers (no favicon/title side effects).
 */

import type { BrandingAssetType, ProductTheme, ThemeBranding } from './interfaces'

export function getThemeBranding(theme: ProductTheme): ThemeBranding {
  return theme.branding
}

export function getThemeBrandingAsset(
  theme: ProductTheme,
  assetType: BrandingAssetType,
): string {
  switch (assetType) {
    case 'logo':
      return theme.branding.logo
    case 'logoMark':
      return theme.branding.logoMark
    case 'favicon':
      return theme.branding.favicon
    case 'icon':
      return theme.branding.icon
    case 'illustrations':
      return theme.branding.illustrations
    default: {
      const _exhaustive: never = assetType
      return _exhaustive
    }
  }
}
