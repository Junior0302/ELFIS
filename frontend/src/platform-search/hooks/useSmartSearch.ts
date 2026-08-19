/**
 * Hook Smart Search — debounce ≥2 chars, abort, cache court, permissions/tenant via auth.
 */

import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../auth'
import { runSmartSearch } from '../sources/smartSearchSources'
import type {
  SearchQuery,
  SearchScope,
  SearchEntityType,
  SmartSearchResponse,
  SmartSearchStatus,
} from '../types'
import { useDebouncedValue } from './useDebouncedValue'

const MIN_QUERY = 2
const DEFAULT_DEBOUNCE = 280
const CACHE_TTL_MS = 8_000

type CacheEntry = { at: number; response: SmartSearchResponse }

export type UseSmartSearchOptions = {
  scope?: SearchScope
  types?: SearchEntityType[]
  enabled?: boolean
  debounceMs?: number
  minChars?: number
  pageSize?: number
  /** Si true, lance une liste initiale même avec q vide (pickers). */
  allowEmptyQuery?: boolean
  filters?: SearchQuery['filters']
}

export function useSmartSearch(rawQuery: string, options: UseSmartSearchOptions = {}) {
  const {
    scope = 'global',
    types,
    enabled = true,
    debounceMs = DEFAULT_DEBOUNCE,
    minChars = MIN_QUERY,
    pageSize = 20,
    allowEmptyQuery = false,
    filters,
  } = options

  const { token, orgId } = useAuth()
  const debouncedQ = useDebouncedValue(rawQuery, debounceMs)
  const [response, setResponse] = useState<SmartSearchResponse | null>(null)
  const [status, setStatus] = useState<SmartSearchStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const cacheRef = useRef<Map<string, CacheEntry>>(new Map())
  const reqId = useRef(0)

  const trimmed = debouncedQ.trim()
  const typing = rawQuery.trim() !== trimmed && rawQuery.trim().length > 0

  const typesKey = types?.join(',') ?? ''

  useEffect(() => {
    if (!enabled) {
      setStatus('idle')
      setResponse(null)
      setErrorMessage(null)
      return
    }

    if (typing) {
      setStatus('typing')
    }

    if (!allowEmptyQuery && trimmed.length > 0 && trimmed.length < minChars) {
      setResponse(null)
      setStatus(trimmed.length === 0 ? 'idle' : 'typing')
      setErrorMessage(null)
      return
    }

    if (!allowEmptyQuery && trimmed.length < minChars) {
      setResponse(null)
      setStatus('idle')
      setErrorMessage(null)
      return
    }

    if (!token) {
      setResponse(null)
      setStatus('idle')
      return
    }

    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      setStatus('offline')
      setErrorMessage('Hors ligne')
      return
    }

    const cacheKey = JSON.stringify({
      q: trimmed,
      scope,
      types: typesKey,
      orgId,
      pageSize,
      filters,
    })
    const cached = cacheRef.current.get(cacheKey)
    if (cached && Date.now() - cached.at < CACHE_TTL_MS) {
      setResponse(cached.response)
      setStatus(cached.response.status)
      setErrorMessage(cached.response.errorMessage ?? null)
      return
    }

    const current = ++reqId.current
    const controller = new AbortController()
    setStatus('loading')
    setErrorMessage(null)

    runSmartSearch(
      {
        q: trimmed,
        scope,
        types,
        page: 1,
        pageSize,
        organizationId: orgId,
        filters,
      },
      { token, orgId, signal: controller.signal },
    )
      .then((res) => {
        if (current !== reqId.current) return
        cacheRef.current.set(cacheKey, { at: Date.now(), response: res })
        setResponse(res)
        setStatus(res.status)
        setErrorMessage(res.errorMessage ?? null)
      })
      .catch((e: Error) => {
        if (current !== reqId.current) return
        if (e?.name === 'AbortError') return
        setResponse(null)
        setStatus('error')
        setErrorMessage(e?.message || 'Erreur de recherche')
      })

    return () => {
      controller.abort()
    }
  }, [
    enabled,
    trimmed,
    typing,
    token,
    orgId,
    scope,
    types,
    typesKey,
    pageSize,
    minChars,
    allowEmptyQuery,
    filters,
  ])

  return {
    response,
    status: typing && status !== 'loading' ? ('typing' as SmartSearchStatus) : status,
    errorMessage,
    items: response?.items ?? [],
    groups: response?.groups ?? [],
    engine: response?.engine,
  }
}
