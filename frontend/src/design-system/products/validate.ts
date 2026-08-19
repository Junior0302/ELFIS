/**
 * Automatic Product Registry validation.
 * Tests must fail if the registry becomes incoherent.
 */

import { PRODUCT_CATEGORIES, isKnownCategoryId } from './categories'
import { PRODUCT_REGISTRY } from './registry'
import { isProductAvailable } from './helpers'
import { PRODUCT_PALETTES } from '../colors/palettes'
import { PRODUCT_ACCENT_GRADIENTS } from '../colors/gradients'
import type {
  ProductId,
  ProductStatus,
  ProductFamily,
  PricingModel,
  RegistryValidationIssue,
  RegistryValidationResult,
} from '../types'

const VALID_STATUSES: ReadonlySet<ProductStatus> = new Set([
  'active',
  'beta',
  'coming_soon',
  'internal',
  'archived',
])

const VALID_FAMILIES: ReadonlySet<ProductFamily> = new Set([
  'platform',
  'pilot_app',
  'shared_service',
  'future_product',
])

const VALID_PRICING: ReadonlySet<PricingModel> = new Set([
  'standalone',
  'bundle',
  'standalone_and_bundle',
  'included',
  'not_available',
])

function issue(
  code: string,
  message: string,
  productId?: ProductId,
): RegistryValidationIssue {
  return { code, message, productId }
}

export function validateProductRegistry(): RegistryValidationResult {
  const issues: RegistryValidationIssue[] = []

  const ids = PRODUCT_REGISTRY.map((p) => p.id)
  const slugs = PRODUCT_REGISTRY.map((p) => p.slug)
  const uniqueIds = new Set(ids)
  const uniqueSlugs = new Set(slugs)

  if (uniqueIds.size !== ids.length) {
    issues.push(issue('duplicate_id', 'Product IDs must be unique'))
  }
  if (uniqueSlugs.size !== slugs.length) {
    issues.push(issue('duplicate_slug', 'Product slugs must be unique'))
  }

  const categoryIds = new Set(PRODUCT_CATEGORIES.map((c) => c.id))
  if (categoryIds.size !== PRODUCT_CATEGORIES.length) {
    issues.push(issue('duplicate_category', 'Category IDs must be unique'))
  }

  const orders = PRODUCT_REGISTRY.map((p) => p.launchOrder)
  const uniqueOrders = new Set(orders)
  if (uniqueOrders.size !== orders.length) {
    issues.push(issue('launch_order_collision', 'launchOrder values must be unique'))
  }
  const sortedOrders = [...orders].sort((a, b) => a - b)
  if (sortedOrders.some((v, i) => i > 0 && v < sortedOrders[i - 1]!)) {
    issues.push(issue('launch_order_unsorted_source', 'launchOrder should be sortable'))
  }

  let activeCount = 0

  for (const product of PRODUCT_REGISTRY) {
    if (!VALID_STATUSES.has(product.status)) {
      issues.push(issue('invalid_status', `Invalid status: ${product.status}`, product.id))
    }
    if (!VALID_FAMILIES.has(product.productFamily)) {
      issues.push(
        issue('invalid_family', `Invalid productFamily: ${product.productFamily}`, product.id),
      )
    }
    if (!VALID_PRICING.has(product.pricingModel)) {
      issues.push(
        issue('invalid_pricing', `Invalid pricingModel: ${product.pricingModel}`, product.id),
      )
    }
    if (!isKnownCategoryId(product.category)) {
      issues.push(
        issue('unknown_category', `Unknown category: ${product.category}`, product.id),
      )
    }
    if (!(product.themeId in PRODUCT_PALETTES)) {
      issues.push(issue('unknown_theme', `Unknown themeId: ${product.themeId}`, product.id))
    }
    if (product.themeId !== product.id) {
      issues.push(
        issue(
          'theme_mismatch',
          `themeId must match product id in V1 (got ${product.themeId})`,
          product.id,
        ),
      )
    }

    const brandingFields = [
      product.logo,
      product.logoMark,
      product.favicon,
      product.branding.icon,
      product.branding.logo,
      product.branding.logoMark,
      product.branding.favicon,
      product.branding.illustrations,
    ]
    if (brandingFields.some((v) => !v || !String(v).trim())) {
      issues.push(issue('empty_branding', 'Branding paths must be non-empty', product.id))
    }
    if (!product.branding.logo.includes('/branding/products/')) {
      issues.push(
        issue(
          'branding_path_convention',
          'Branding paths must live under /branding/products/',
          product.id,
        ),
      )
    }

    if (!product.illustrationStyle) {
      issues.push(issue('missing_illustration', 'illustrationStyle required', product.id))
    }
    if (!product.accentGradient?.from || !product.accentGradient?.to) {
      issues.push(issue('missing_gradient', 'accentGradient required', product.id))
    }
    if (!(product.id in PRODUCT_ACCENT_GRADIENTS)) {
      issues.push(issue('gradient_registry_gap', 'Missing accent gradient entry', product.id))
    }

    if (!product.tagline?.trim() || !product.shortDescription?.trim()) {
      issues.push(issue('missing_copy', 'tagline and shortDescription required', product.id))
    }
    if (product.capabilities && product.capabilities.length > 3) {
      issues.push(
        issue('capabilities_overflow', 'capabilities should list at most 3 labels', product.id),
      )
    }
    if (!product.slug?.trim() || product.slug.includes(' ')) {
      issues.push(issue('invalid_slug', 'slug must be non-empty without spaces', product.id))
    }

    if (product.status === 'active') activeCount += 1

    // coming_soon must not be treated as available
    if (product.status === 'coming_soon' && isProductAvailable(product.id)) {
      issues.push(
        issue(
          'coming_soon_available',
          'coming_soon products must not be available',
          product.id,
        ),
      )
    }
    if (product.status === 'coming_soon' && product.availableForSubscription) {
      issues.push(
        issue(
          'coming_soon_subscription',
          'coming_soon products must not be available for subscription',
          product.id,
        ),
      )
    }
    if (product.status === 'coming_soon' && product.availableInLauncher) {
      issues.push(
        issue(
          'coming_soon_launcher',
          'coming_soon products must not be exposed in launcher yet',
          product.id,
        ),
      )
    }

    // Subscription / status coherence
    if (product.availableForSubscription && product.status !== 'active' && product.status !== 'beta') {
      issues.push(
        issue(
          'subscription_status',
          'availableForSubscription requires active or beta status',
          product.id,
        ),
      )
    }
    if (
      product.pricingModel === 'included' &&
      (product.standaloneEligible || product.availableForSubscription)
    ) {
      issues.push(
        issue(
          'included_standalone',
          'included products must not be standalone-subscribable',
          product.id,
        ),
      )
    }

    if (product.id === 'elfis-core') {
      if (product.productFamily !== 'platform') {
        issues.push(issue('core_family', 'ELFIS Core must be platform', product.id))
      }
      if (product.standaloneEligible || product.pricingModel !== 'included') {
        issues.push(
          issue(
            'core_not_standalone',
            'ELFIS Core must be included, never standalone subscription',
            product.id,
          ),
        )
      }
    } else if (product.productFamily !== 'pilot_app') {
      issues.push(
        issue(
          'pilot_family',
          `Expected pilot_app for Pilot apps (got ${product.productFamily})`,
          product.id,
        ),
      )
    }
  }

  if (activeCount < 1) {
    issues.push(issue('no_active_product', 'At least one product must be active'))
  }

  return { ok: issues.length === 0, issues }
}
