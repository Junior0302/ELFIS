/**
 * Launcher view-model helpers — pure, no React.
 * Continuer = lastProduct only (never invent history).
 */

import { getProductById, isKnownProductId } from '../design-system/products/helpers'
import { getCategoryLabel, resolveLauncherProductState, STATE_LABELS } from './launcherState'
import type {
  LauncherFooterLink,
  LauncherResolveContext,
  LauncherSections,
  ResolvedLauncherProduct,
} from './launcher.types'
import { getLastProductId } from '../home/lastProduct'
import { getProductEntryRoute } from './productEntryRoutes'

/** Footer links with real SPA routes only — hide unbranched destinations. */
export const LAUNCHER_FOOTER_LINKS: readonly LauncherFooterLink[] = [
  { id: 'home', label: 'Accueil ELFIS', to: '/home' },
  { id: 'org', label: 'Organisation', to: '/platform/organization' },
  { id: 'documents', label: 'Documents', to: '/platform/documents' },
  { id: 'relations', label: 'Relations', to: '/platform/relations' },
  { id: 'communications', label: 'Communications', to: '/platform/communications' },
  { id: 'settings', label: 'Paramètres', to: '/platform/settings' },
]

export function getLauncherFooterLinks(): readonly LauncherFooterLink[] {
  return LAUNCHER_FOOTER_LINKS
}

export function getProductCapabilities(item: ResolvedLauncherProduct): readonly string[] {
  const caps = item.product.capabilities
  if (caps && caps.length > 0) return caps.slice(0, 3)
  return []
}

export function getLauncherDescription(item: ResolvedLauncherProduct): string {
  return (
    item.product.launcherDescription?.trim() ||
    item.product.shortDescription?.trim() ||
    item.product.tagline
  )
}

function collectAll(sections: LauncherSections): ResolvedLauncherProduct[] {
  const out: ResolvedLauncherProduct[] = []
  const seen = new Set<string>()
  const push = (item: ResolvedLauncherProduct | null | undefined) => {
    if (!item || seen.has(item.product.id)) return
    seen.add(item.product.id)
    out.push(item)
  }
  push(sections.active)
  sections.available.forEach(push)
  sections.locked.forEach(push)
  sections.comingSoonFeatured.forEach(push)
  sections.comingSoonGrouped.forEach(push)
  return out
}

/** Available section: active + available + locked (openable surface). */
export function getAvailableDisplayItems(sections: LauncherSections): ResolvedLauncherProduct[] {
  const out: ResolvedLauncherProduct[] = []
  const seen = new Set<string>()
  const push = (item: ResolvedLauncherProduct | null | undefined) => {
    if (!item || seen.has(item.product.id)) return
    seen.add(item.product.id)
    out.push(item)
  }
  push(sections.active)
  sections.available.forEach(push)
  sections.locked.forEach(push)
  return out
}

export function getComingSoonDisplayItems(sections: LauncherSections): {
  featured: ResolvedLauncherProduct[]
  grouped: ResolvedLauncherProduct[]
} {
  return {
    featured: sections.comingSoonFeatured,
    grouped: sections.comingSoonGrouped,
  }
}

/**
 * Real last app only. Marks isLastUsed.
 * Fallback ComptaPilot CTA when none — returned separately as `fallbackContinue`.
 */
export function resolveContinueItem(
  sections: LauncherSections,
  context: LauncherResolveContext,
  lastProductId: string | null = getLastProductId(),
): {
  continueItem: ResolvedLauncherProduct | null
  fallbackContinue: ResolvedLauncherProduct | null
} {
  const all = collectAll(sections)

  if (lastProductId && isKnownProductId(lastProductId)) {
    const found = all.find((i) => i.product.id === lastProductId)
    if (found) {
      return {
        continueItem: { ...found, isLastUsed: true },
        fallbackContinue: null,
      }
    }
    try {
      const resolved = resolveLauncherProductState(getProductById(lastProductId), context)
      return {
        continueItem: { ...resolved, isLastUsed: true },
        fallbackContinue: null,
      }
    } catch {
      /* fall through */
    }
  }

  /* No invented history — offer Commencer avec ComptaPilot */
  try {
    const compta = getProductById('comptapilot')
    const route = getProductEntryRoute('comptapilot') ?? undefined
    const canOpen = Boolean(route && context.availableRoutes.has(route))
    const isActive = context.currentProductId === 'comptapilot'
    return {
      continueItem: null,
      fallbackContinue: {
        product: compta,
        state: isActive ? 'active' : canOpen ? 'available' : 'unavailable',
        canOpen: canOpen && !isActive,
        route,
        label: isActive ? STATE_LABELS.active : STATE_LABELS.available,
        isLastUsed: false,
      },
    }
  } catch {
    return { continueItem: null, fallbackContinue: null }
  }
}

export function matchesLauncherQuery(item: ResolvedLauncherProduct, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  const p = item.product
  const haystack = [
    p.displayName,
    p.shortName,
    p.tagline,
    p.shortDescription,
    p.launcherDescription ?? '',
    p.category,
    getCategoryLabel(p),
    item.state,
    item.label,
    STATE_LABELS[item.state],
    ...(p.capabilities ?? []),
  ]
    .join(' ')
    .toLowerCase()
  return haystack.includes(q)
}

export function filterLauncherItems(
  items: ResolvedLauncherProduct[],
  query: string,
): ResolvedLauncherProduct[] {
  if (!query.trim()) return items
  return items.filter((item) => matchesLauncherQuery(item, query))
}

export function collectSearchableItems(sections: LauncherSections): ResolvedLauncherProduct[] {
  return collectAll(sections)
}
