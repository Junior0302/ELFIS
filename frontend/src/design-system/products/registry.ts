/**
 * Product Registry — single source of truth for ELFIS products.
 * E1.1.1 extends ProductIdentity (family, category, commercial prep, branding).
 */

import { PRODUCT_PALETTES } from '../colors/palettes'
import { PRODUCT_ACCENT_GRADIENTS } from '../colors/gradients'
import { brandingPathsFor } from '../branding/assets'
import type {
  ProductIdentity,
  ProductId,
  ProductStatus,
  IllustrationStyle,
  PricingModel,
  ProductFamily,
  ProductCategoryId,
} from '../types'

type ProductSeed = {
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
  illustrationStyle: IllustrationStyle
  websitePath: string
  documentationPath: string
  supportEmail?: string
  launchOrder: number
  availableInLauncher: boolean
  availableForSubscription: boolean
  standaloneEligible: boolean
  bundleEligible: boolean
  defaultBundleIds?: readonly string[]
  pricingModel: PricingModel
  featureFlags?: Readonly<Record<string, boolean>>
  capabilities?: readonly string[]
  featuredInLauncher?: boolean
  launcherDescription?: string
}

function defineProduct(seed: ProductSeed): ProductIdentity {
  const branding = brandingPathsFor(seed.id)
  const colors = PRODUCT_PALETTES[seed.id]
  return {
    id: seed.id,
    slug: seed.slug,
    displayName: seed.displayName,
    shortName: seed.shortName,
    productFamily: seed.productFamily,
    category: seed.category,
    tagline: seed.tagline,
    shortDescription: seed.shortDescription,
    longDescription: seed.longDescription,
    status: seed.status,
    themeId: seed.id,
    iconKey: seed.id,
    logo: branding.logo,
    logoMark: branding.logoMark,
    favicon: branding.favicon,
    accentGradient: PRODUCT_ACCENT_GRADIENTS[seed.id],
    marketingColor: colors.primaryColor,
    illustrationStyle: seed.illustrationStyle,
    websitePath: seed.websitePath,
    documentationPath: seed.documentationPath,
    supportEmail: seed.supportEmail,
    launchOrder: seed.launchOrder,
    availableInLauncher: seed.availableInLauncher,
    availableForSubscription: seed.availableForSubscription,
    standaloneEligible: seed.standaloneEligible,
    bundleEligible: seed.bundleEligible,
    defaultBundleIds: seed.defaultBundleIds ?? [],
    pricingModel: seed.pricingModel,
    colors,
    branding,
    featureFlags: seed.featureFlags,
    capabilities: seed.capabilities,
    featuredInLauncher: seed.featuredInLauncher,
    launcherDescription: seed.launcherDescription,
  }
}

export const PRODUCT_REGISTRY: readonly ProductIdentity[] = [
  defineProduct({
    id: 'elfis-core',
    slug: 'elfis-core',
    displayName: 'ELFIS Core',
    shortName: 'ELFIS',
    productFamily: 'platform',
    category: 'platform',
    tagline: 'La plateforme qui relie vos outils, vos données et vos décisions.',
    shortDescription:
      'Le socle central de la suite ELFIS : compte, organisation, sécurité, abonnements, recherche, décisions et services partagés.',
    status: 'active',
    illustrationStyle: 'platform_minimal',
    websitePath: '/products/elfis-core',
    documentationPath: '/docs/products/elfis-core',
    supportEmail: 'support@elfis.app',
    launchOrder: 1,
    availableInLauncher: true,
    availableForSubscription: false,
    standaloneEligible: false,
    bundleEligible: false,
    pricingModel: 'included',
    capabilities: ['Compte', 'Organisation', 'Sécurité'],
  }),
  defineProduct({
    id: 'comptapilot',
    slug: 'comptapilot',
    displayName: 'ComptaPilot',
    shortName: 'Compta',
    productFamily: 'pilot_app',
    category: 'finance',
    tagline: 'Pilotez votre comptabilité et vos finances avec clarté.',
    shortDescription:
      'Facturation, documents, comptabilité, trésorerie et décisions financières réunis dans un seul espace.',
    launcherDescription: 'Finance, facturation et pilotage comptable.',
    status: 'active',
    illustrationStyle: 'financial_data',
    websitePath: '/products/comptapilot',
    documentationPath: '/docs/products/comptapilot',
    launchOrder: 2,
    availableInLauncher: true,
    availableForSubscription: true,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Facturation', 'Banque', 'Pilotage'],
    featuredInLauncher: true,
  }),
  defineProduct({
    id: 'salespilot',
    slug: 'salespilot',
    displayName: 'SalesPilot',
    shortName: 'Sales',
    productFamily: 'pilot_app',
    category: 'sales',
    tagline: 'Transformez vos opportunités en revenus.',
    shortDescription:
      'Prospects, clients, pipeline, devis, relances et suivi commercial connectés à votre gestion.',
    launcherDescription: 'Pipeline, CRM et opportunités commerciales.',
    /** Beta interne en développement uniquement — Coming Soon en production. */
    status: import.meta.env.DEV ? 'beta' : 'coming_soon',
    illustrationStyle: 'sales_pipeline',
    websitePath: '/products/salespilot',
    documentationPath: '/docs/products/salespilot',
    launchOrder: 3,
    availableInLauncher: import.meta.env.DEV,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Pipeline', 'CRM', 'Propositions'],
    featuredInLauncher: true,
  }),
  defineProduct({
    id: 'docpilot',
    slug: 'docpilot',
    displayName: 'DocPilot',
    shortName: 'Docs',
    productFamily: 'pilot_app',
    category: 'documents',
    tagline: 'Centralisez, comprenez et retrouvez vos documents.',
    shortDescription:
      'Coffre documentaire, OCR, recherche intelligente, classement et suivi des documents professionnels.',
    launcherDescription: 'Documents et flux documentaires.',
    status: 'coming_soon',
    illustrationStyle: 'document_intelligence',
    websitePath: '/products/docpilot',
    documentationPath: '/docs/products/docpilot',
    launchOrder: 4,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Coffre', 'OCR', 'Recherche'],
    featuredInLauncher: true,
  }),
  defineProduct({
    id: 'hrpilot',
    slug: 'hrpilot',
    displayName: 'HRPilot',
    shortName: 'HR',
    productFamily: 'pilot_app',
    category: 'people',
    tagline: 'Simplifiez la gestion de vos équipes.',
    shortDescription:
      'Collaborateurs, documents RH, absences, suivi et processus internes.',
    launcherDescription: 'Équipes, congés et processus RH.',
    status: 'coming_soon',
    illustrationStyle: 'people_operations',
    websitePath: '/products/hrpilot',
    documentationPath: '/docs/products/hrpilot',
    launchOrder: 5,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Équipes', 'Congés', 'Onboarding'],
    featuredInLauncher: true,
  }),
  defineProduct({
    id: 'legalpilot',
    slug: 'legalpilot',
    displayName: 'LegalPilot',
    shortName: 'Legal',
    productFamily: 'pilot_app',
    category: 'legal',
    tagline: 'Gardez le contrôle sur vos obligations juridiques.',
    shortDescription: 'Contrats, échéances, conformité et documents légaux centralisés.',
    status: 'coming_soon',
    illustrationStyle: 'legal_precision',
    websitePath: '/products/legalpilot',
    documentationPath: '/docs/products/legalpilot',
    launchOrder: 6,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Contrats', 'Échéances', 'Conformité'],
  }),
  defineProduct({
    id: 'inventorypilot',
    slug: 'inventorypilot',
    displayName: 'InventoryPilot',
    shortName: 'Stock',
    productFamily: 'pilot_app',
    category: 'operations',
    tagline: 'Maîtrisez vos stocks et vos flux.',
    shortDescription:
      'Inventaire, mouvements, approvisionnements, alertes et suivi opérationnel.',
    status: 'coming_soon',
    illustrationStyle: 'inventory_flow',
    websitePath: '/products/inventorypilot',
    documentationPath: '/docs/products/inventorypilot',
    launchOrder: 7,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Inventaire', 'Mouvements', 'Alertes'],
  }),
  defineProduct({
    id: 'marketingpilot',
    slug: 'marketingpilot',
    displayName: 'MarketingPilot',
    shortName: 'Marketing',
    productFamily: 'pilot_app',
    category: 'marketing',
    tagline: 'Structurez et mesurez votre croissance.',
    shortDescription:
      'Campagnes, contenus, canaux, performances et coordination marketing.',
    status: 'coming_soon',
    illustrationStyle: 'marketing_growth',
    websitePath: '/products/marketingpilot',
    documentationPath: '/docs/products/marketingpilot',
    launchOrder: 8,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Campagnes', 'Canaux', 'Performances'],
  }),
  defineProduct({
    id: 'projectpilot',
    slug: 'projectpilot',
    displayName: 'ProjectPilot',
    shortName: 'Projects',
    productFamily: 'pilot_app',
    category: 'projects',
    tagline: 'Pilotez vos projets de bout en bout.',
    shortDescription:
      'Missions, tâches, délais, budgets, équipes et rentabilité des projets.',
    status: 'coming_soon',
    illustrationStyle: 'project_collaboration',
    websitePath: '/products/projectpilot',
    documentationPath: '/docs/products/projectpilot',
    launchOrder: 9,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Missions', 'Délais', 'Budgets'],
  }),
  defineProduct({
    id: 'supportpilot',
    slug: 'supportpilot',
    displayName: 'SupportPilot',
    shortName: 'Support',
    productFamily: 'pilot_app',
    category: 'support',
    tagline: 'Offrez un meilleur suivi à vos clients.',
    shortDescription:
      'Demandes, tickets, priorités, réponses et historique du service client.',
    launcherDescription: 'Tickets et relation client.',
    status: 'coming_soon',
    illustrationStyle: 'customer_support',
    websitePath: '/products/supportpilot',
    documentationPath: '/docs/products/supportpilot',
    launchOrder: 10,
    availableInLauncher: false,
    availableForSubscription: false,
    standaloneEligible: true,
    bundleEligible: true,
    pricingModel: 'standalone_and_bundle',
    capabilities: ['Tickets', 'SLA', 'Base de savoir'],
    featuredInLauncher: true,
  }),
] as const

const BY_ID: Record<ProductId, ProductIdentity> = PRODUCT_REGISTRY.reduce(
  (acc, product) => {
    acc[product.id] = product
    return acc
  },
  {} as Record<ProductId, ProductIdentity>,
)

const BY_SLUG: Record<string, ProductIdentity> = PRODUCT_REGISTRY.reduce(
  (acc, product) => {
    acc[product.slug] = product
    return acc
  },
  {} as Record<string, ProductIdentity>,
)

/** @deprecated Prefer getProductById — kept for E1.1 callers. */
export function getProduct(id: ProductId): ProductIdentity {
  return BY_ID[id]
}

export function getProductById(id: ProductId): ProductIdentity {
  return BY_ID[id]
}

export function getProductBySlug(slug: string): ProductIdentity | undefined {
  return BY_SLUG[slug]
}

export function listProducts(status?: ProductStatus): ProductIdentity[] {
  if (!status) return [...PRODUCT_REGISTRY]
  return PRODUCT_REGISTRY.filter((p) => p.status === status)
}

export function listActiveProducts(): ProductIdentity[] {
  return listProducts('active')
}

export function isKnownProductId(value: string): value is ProductId {
  return value in BY_ID
}

/** Current runtime product for the SPA until multi-Pilot routing exists. */
export const DEFAULT_RUNTIME_PRODUCT_ID: ProductId = 'comptapilot'
