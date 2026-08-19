/**
 * Hook Smart Library — list / filter / pagination / cache court.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../../auth'
import { useDebouncedValue } from '../../platform-search/hooks/useDebouncedValue'
import {
  DISABLED_FAVORITES,
  DISABLED_MOST_USED,
  DISABLED_RECENTS,
} from '../contracts/libraryMeta'
import { getActiveResourceSource } from '../sources/resolveResourceSource'
import type {
  LibraryNavSection,
  Resource,
  ResourceKind,
  ResourceListResult,
  ResourceSort,
  ResourceStatus,
} from '../types'

export type SmartLibraryFilters = {
  q: string
  section: LibraryNavSection
  kinds: ResourceKind[]
  status: ResourceStatus | 'any'
  vatRates: number[]
  priceMin: number | null
  priceMax: number | null
  sort: ResourceSort
  activeOnly: boolean
}

const DEFAULT_FILTERS: SmartLibraryFilters = {
  q: '',
  section: 'all',
  kinds: [],
  status: 'any',
  vatRates: [],
  priceMin: null,
  priceMax: null,
  sort: 'name_asc',
  activeOnly: false,
}

const CACHE_TTL_MS = 20_000

type CacheEntry = { key: string; at: number; result: ResourceListResult }

function sectionToKinds(section: LibraryNavSection): ResourceKind[] | undefined {
  if (section === 'products') return ['product']
  if (section === 'services') return ['service']
  if (section === 'packs') return ['pack']
  return undefined
}

function isMetaSection(section: LibraryNavSection): boolean {
  return section === 'favorites' || section === 'recents' || section === 'most_used'
}

export function useResourceLibrary(initial?: Partial<SmartLibraryFilters>) {
  const { token, orgId } = useAuth()
  const source = useMemo(() => getActiveResourceSource(), [])
  const [filters, setFilters] = useState<SmartLibraryFilters>({
    ...DEFAULT_FILTERS,
    ...initial,
  })
  const debouncedQ = useDebouncedValue(filters.q, 220)
  const [result, setResult] = useState<ResourceListResult>({
    items: [],
    total: 0,
    page: 1,
    pageSize: 24,
    hasMore: false,
  })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [reloadTick, setReloadTick] = useState(0)
  const cacheRef = useRef<CacheEntry | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const metaDisabledReason = useMemo(() => {
    if (filters.section === 'favorites') return DISABLED_FAVORITES.reasonDisabled
    if (filters.section === 'recents') return DISABLED_RECENTS.reasonDisabled
    if (filters.section === 'most_used') return DISABLED_MOST_USED.reasonDisabled
    if (filters.section === 'packs') {
      return source.capabilities.packs
        ? undefined
        : 'Les packs ne sont pas supportés par la bibliothèque locale V1.'
    }
    return undefined
  }, [filters.section, source.capabilities.packs])

  const load = useCallback(async () => {
    if (!token) return
    if (isMetaSection(filters.section) || filters.section === 'packs') {
      setResult({ items: [], total: 0, page: 1, pageSize: 24, hasMore: false })
      setLoading(false)
      setError('')
      return
    }

    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    const kindsFromSection = sectionToKinds(filters.section)
    const kinds =
      filters.kinds.length > 0 ? filters.kinds : kindsFromSection ?? []

    const cacheKey = JSON.stringify({
      q: debouncedQ,
      kinds,
      status: filters.status,
      vatRates: filters.vatRates,
      priceMin: filters.priceMin,
      priceMax: filters.priceMax,
      sort: filters.sort,
      activeOnly: filters.activeOnly,
      page,
      orgId,
    })

    const cached = cacheRef.current
    if (cached && cached.key === cacheKey && Date.now() - cached.at < CACHE_TTL_MS) {
      setResult(cached.result)
      setLoading(false)
      setError('')
      return
    }

    setLoading(true)
    setError('')
    try {
      const res = await source.list({
        q: debouncedQ,
        token,
        orgId,
        kinds: kinds.length ? kinds : undefined,
        status: filters.status,
        vatRates: filters.vatRates.length ? filters.vatRates : undefined,
        priceMin: filters.priceMin,
        priceMax: filters.priceMax,
        sort: filters.sort,
        activeOnly: filters.activeOnly,
        page,
        pageSize: 24,
        signal: ac.signal,
      })
      if (ac.signal.aborted) return
      cacheRef.current = { key: cacheKey, at: Date.now(), result: res }
      setResult(res)
    } catch (e) {
      if (ac.signal.aborted) return
      setError(e instanceof Error ? e.message : 'Impossible de charger la bibliothèque')
      setResult({ items: [], total: 0, page: 1, pageSize: 24, hasMore: false })
    } finally {
      if (!ac.signal.aborted) setLoading(false)
    }
  }, [token, orgId, source, filters, debouncedQ, page, reloadTick])

  useEffect(() => {
    void load()
    return () => abortRef.current?.abort()
  }, [load])

  const updateFilters = useCallback((patch: Partial<SmartLibraryFilters>) => {
    setPage(1)
    setFilters((prev) => ({ ...prev, ...patch }))
  }, [])

  const reload = useCallback(() => {
    cacheRef.current = null
    setReloadTick((t) => t + 1)
  }, [])

  const availableVatRates = useMemo(() => {
    const set = new Set(result.items.map((r) => r.vatRate))
    return [...set].sort((a, b) => a - b)
  }, [result.items])

  return {
    source,
    filters,
    updateFilters,
    result,
    items: result.items as Resource[],
    page,
    setPage,
    loading,
    error,
    metaDisabledReason,
    availableVatRates,
    reload,
    capabilities: source.capabilities,
  }
}
