/**
 * Search Engine V1 client hook — unique search source of truth.
 * Uses api.searchElfis only (no second indexing / engine).
 */

import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import type { CommandSearchStatus, SearchEngineHit } from './commandTypes'

const DEBOUNCE_MS = 280
const MIN_QUERY = 2
const PAGE_SIZE = 12

export function useCommandSearch(
  query: string,
  enabled: boolean,
  commandMode: boolean,
  retryKey = 0,
) {
  const { token, orgId } = useAuth()
  const [hits, setHits] = useState<SearchEngineHit[]>([])
  const [status, setStatus] = useState<CommandSearchStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const timer = useRef<number | null>(null)
  const reqId = useRef(0)

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current)

    if (!enabled || commandMode) {
      setHits([])
      setStatus('idle')
      setErrorMessage(null)
      return
    }

    const q = query.trim()
    if (q.length < MIN_QUERY) {
      setHits([])
      setStatus('idle')
      setErrorMessage(null)
      return
    }

    if (!token) {
      setHits([])
      setStatus('idle')
      return
    }

    setStatus('loading')
    setErrorMessage(null)
    const current = ++reqId.current

    timer.current = window.setTimeout(() => {
      api
        .searchElfis({ q, page: 1, page_size: PAGE_SIZE, sort: 'relevance' }, token, orgId)
        .then((res) => {
          if (current !== reqId.current) return
          const items = (res.items ?? []) as SearchEngineHit[]
          setHits(items)
          setStatus(items.length === 0 ? 'empty' : 'ready')
        })
        .catch((e: Error) => {
          if (current !== reqId.current) return
          setHits([])
          setStatus('error')
          setErrorMessage(e?.message || 'Erreur de recherche')
        })
    }, DEBOUNCE_MS)

    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [query, enabled, commandMode, token, orgId, retryKey])

  return { hits, status, errorMessage }
}
