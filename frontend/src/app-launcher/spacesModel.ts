/**
 * Résolution hub Espaces — pure, sans React.
 * Pas de fausse page : canOpen seulement si entryRoute ∈ availableRoutes.
 */

import { getLastProductAt, getLastProductId } from '../home/lastProduct'
import { ELFIS_SPACES, getSpaceByProductId } from './spacesCatalog'
import type { LauncherResolveContext } from './launcher.types'
import type { ResolvedSpace, SpaceDefinition, SpaceSections } from './spaces.types'

const SPACE_STATE_LABELS = {
  active: 'Espace actif',
  available: 'Ouvrir',
  locked: 'Non inclus dans votre abonnement',
  coming_soon: 'Bientôt',
  beta: 'Bêta',
  unavailable: 'Indisponible',
} as const

function productGateAllows(space: SpaceDefinition): boolean {
  /* Hub espaces : ouverture = route SPA réelle (pas de fausse page). */
  return Boolean(space.entryRoute)
}

export function resolveSpaceState(
  space: SpaceDefinition,
  context: LauncherResolveContext,
): ResolvedSpace {
  const route = space.entryRoute ?? undefined
  const hasRoute = Boolean(route && context.availableRoutes.has(route))

  if (!route || !hasRoute) {
    return {
      space,
      state: 'coming_soon',
      canOpen: false,
      label: SPACE_STATE_LABELS.coming_soon,
      reason: 'Cet espace sera bientôt disponible.',
    }
  }

  const pid = space.engineProductId
  if (pid && context.currentProductId === pid) {
    return {
      space,
      state: 'active',
      canOpen: true,
      route,
      label: SPACE_STATE_LABELS.active,
    }
  }

  if (pid && context.entitlements && pid in context.entitlements && !context.entitlements[pid]) {
    return {
      space,
      state: 'locked',
      canOpen: false,
      route,
      label: SPACE_STATE_LABELS.locked,
      reason: 'Disponible avec une autre offre',
    }
  }

  if (!productGateAllows(space)) {
    return {
      space,
      state: 'coming_soon',
      canOpen: false,
      route,
      label: SPACE_STATE_LABELS.coming_soon,
      reason: 'Cet espace sera bientôt disponible.',
    }
  }

  return {
    space,
    state: 'available',
    canOpen: true,
    route,
    label: SPACE_STATE_LABELS.available,
  }
}

export function buildSpaceSections(context: LauncherResolveContext): SpaceSections {
  const available: ResolvedSpace[] = []
  const comingSoon: ResolvedSpace[] = []

  for (const def of ELFIS_SPACES) {
    const resolved = resolveSpaceState(def, context)
    if (resolved.state === 'coming_soon' || resolved.state === 'unavailable') {
      comingSoon.push(resolved)
    } else {
      available.push(resolved)
    }
  }

  return { available, comingSoon }
}

export function collectAllSpaces(sections: SpaceSections): ResolvedSpace[] {
  return [...sections.available, ...sections.comingSoon]
}

/**
 * Continuer = lastProduct réel → espace métier.
 * Fallback Finance (pas d’historique inventé).
 */
export function resolveContinueSpace(
  sections: SpaceSections,
  context: LauncherResolveContext,
  lastProductId: string | null = getLastProductId(),
  lastAt: string | null = getLastProductAt(),
): {
  continueItem: ResolvedSpace | null
  fallbackContinue: ResolvedSpace | null
} {
  const all = collectAllSpaces(sections)

  if (lastProductId) {
    const spaceDef = getSpaceByProductId(lastProductId)
    if (spaceDef) {
      const found = all.find((s) => s.space.id === spaceDef.id)
      if (found) {
        return {
          continueItem: { ...found, isLastUsed: true, lastActivityAt: lastAt },
          fallbackContinue: null,
        }
      }
      const resolved = resolveSpaceState(spaceDef, context)
      return {
        continueItem: { ...resolved, isLastUsed: true, lastActivityAt: lastAt },
        fallbackContinue: null,
      }
    }
  }

  const finance = all.find((s) => s.space.id === 'finance')
  if (finance) {
    return { continueItem: null, fallbackContinue: { ...finance, isLastUsed: false } }
  }

  return { continueItem: null, fallbackContinue: null }
}

export function matchesSpaceQuery(item: ResolvedSpace, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  const s = item.space
  const haystack = [
    s.title,
    s.description,
    s.engineLabel ?? '',
    s.engineProductId ?? '',
    item.state,
    item.label,
    ...s.capabilities,
    ...s.searchAliases,
    ...s.shortcuts.map((sc) => `${sc.label} ${sc.to}`),
    s.entryRoute ?? '',
  ]
    .join(' ')
    .toLowerCase()
  return haystack.includes(q)
}

export function filterSpaces(items: ResolvedSpace[], query: string): ResolvedSpace[] {
  if (!query.trim()) return items
  return items.filter((item) => matchesSpaceQuery(item, query))
}

export function formatSpaceActivity(iso: string | null | undefined): string | null {
  if (!iso) return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  const diff = Date.now() - t
  if (diff < 60_000) return 'À l’instant'
  if (diff < 3_600_000) return `Il y a ${Math.floor(diff / 60_000)} min`
  if (diff < 86_400_000) return `Il y a ${Math.floor(diff / 3_600_000)} h`
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(t))
  } catch {
    return null
  }
}

export { SPACE_STATE_LABELS }
