/**
 * Pure product helpers — no React, no DOM.
 * Ready for App Launcher, marketing, nav, subscriptions (future).
 */

import { getCategoryById } from './categories'
import {
  getProductById,
  getProductBySlug,
  isKnownProductId,
  PRODUCT_REGISTRY,
} from './registry'
import type {
  ProductCategory,
  ProductCategoryId,
  ProductId,
  ProductIdentity,
} from '../types'

export { getProductById, getProductBySlug, isKnownProductId }

export function getProductsByCategory(categoryId: ProductCategoryId): ProductIdentity[] {
  return PRODUCT_REGISTRY.filter((p) => p.category === categoryId).sort(
    (a, b) => a.launchOrder - b.launchOrder,
  )
}

/** Products flagged for future App Launcher exposure. */
export function getLauncherProducts(): ProductIdentity[] {
  return PRODUCT_REGISTRY.filter((p) => p.availableInLauncher).sort(
    (a, b) => a.launchOrder - b.launchOrder,
  )
}

export function getActiveProducts(): ProductIdentity[] {
  return PRODUCT_REGISTRY.filter((p) => p.status === 'active').sort(
    (a, b) => a.launchOrder - b.launchOrder,
  )
}

export function getComingSoonProducts(): ProductIdentity[] {
  return PRODUCT_REGISTRY.filter((p) => p.status === 'coming_soon').sort(
    (a, b) => a.launchOrder - b.launchOrder,
  )
}

/**
 * Products eligible to be sold standalone when commercially available.
 * Filters on commercial flags — does not imply current availability.
 */
export function getStandaloneProducts(): ProductIdentity[] {
  return PRODUCT_REGISTRY.filter(
    (p) =>
      p.standaloneEligible &&
      (p.pricingModel === 'standalone' || p.pricingModel === 'standalone_and_bundle'),
  ).sort((a, b) => a.launchOrder - b.launchOrder)
}

export function getBundleEligibleProducts(): ProductIdentity[] {
  return PRODUCT_REGISTRY.filter((p) => p.bundleEligible).sort(
    (a, b) => a.launchOrder - b.launchOrder,
  )
}

export function getProductCategory(productId: ProductId): ProductCategory {
  const product = getProductById(productId)
  return getCategoryById(product.category)
}

/**
 * Runtime availability for product surfaces (nav, launcher actions).
 * coming_soon / internal / archived are never available.
 */
export function isProductAvailable(productId: ProductId): boolean {
  const product = getProductById(productId)
  return product.status === 'active' || product.status === 'beta'
}
