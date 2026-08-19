/**
 * Branding asset path conventions — placeholders only.
 * No definitive binary assets are shipped in E1.1.1.
 */

import type { ProductBrandingAssets, ProductId } from '../types'

const BRANDING_ROOT = '/branding/products'

export function brandingPathsFor(productId: ProductId): ProductBrandingAssets {
  const base = `${BRANDING_ROOT}/${productId}`
  return {
    icon: `${base}/icon.svg`,
    logo: `${base}/logo.svg`,
    logoMark: `${base}/logo-mark.svg`,
    favicon: `${base}/favicon.svg`,
    illustrations: `${base}/illustrations/`,
  }
}

/**
 * Expected folder layout under `public/branding/` (binaries in later milestones):
 *
 * public/branding/
 *   products/
 *     elfis-core/{logo,logo-mark,icon,favicon}.svg + illustrations/
 *     comptapilot/...
 *     ...
 *   shared/illustrations/
 *   shared/marketing/
 */
export const BRANDING_ASSET_KINDS = [
  'icon',
  'logo',
  'logoMark',
  'favicon',
  'illustrations',
] as const

export type BrandingAssetKind = (typeof BRANDING_ASSET_KINDS)[number]

export const BRANDING_SHARED_PATHS = {
  illustrations: '/branding/shared/illustrations',
  marketing: '/branding/shared/marketing',
} as const

export const BRANDING_PRODUCTS_ROOT = BRANDING_ROOT
