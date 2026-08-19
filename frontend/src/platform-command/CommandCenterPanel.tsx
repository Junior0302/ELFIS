import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from 'react'
import { CommandCenterHeader } from './CommandCenterHeader'
import { CommandInput } from './CommandInput'
import { CommandResults } from './CommandResults'
import { RecentSearches } from './RecentSearches'
import { SearchFooter } from './SearchFooter'
import {
  buildResultGroups,
  flattenGroups,
  parseCommandMode,
  searchPageHref,
} from './commandModel'
import { clearRecentSearches, getRecentSearches, pushRecentSearch } from './recentSearchesStorage'
import { useCommandSearch } from './useCommandSearch'
import type { CommandResultItem } from './commandTypes'
import { cx } from '../design-system/components/cx'
import { trackProductEvent } from '../productEvents'

export type CommandCenterPanelProps = {
  open: boolean
  onNavigate: (href: string, meta?: { kind?: string; title?: string }) => void
  onClose: () => void
  embedded?: boolean
  panelId?: string
  inputRef?: RefObject<HTMLInputElement | null>
}

export function CommandCenterPanel({
  open,
  onNavigate,
  onClose,
  embedded = false,
  panelId,
  inputRef,
}: CommandCenterPanelProps) {
  const [query, setQuery] = useState('')
  const [recent, setRecent] = useState<string[]>(() => getRecentSearches())
  const [activeId, setActiveId] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const titleId = useId()
  const descId = useId()
  const inputId = useId()
  const searchTracked = useRef(false)
  const localInputRef = useRef<HTMLInputElement>(null)
  const resolvedInputRef = inputRef ?? localInputRef

  const commandMode = useMemo(() => parseCommandMode(query), [query])
  const searchQuery = commandMode.active ? '' : query
  const { hits, status, errorMessage } = useCommandSearch(
    searchQuery,
    open,
    commandMode.active,
    retryKey,
  )

  const groups = useMemo(
    () =>
      buildResultGroups({
        query: commandMode.active ? '' : query,
        commandMode,
        searchHits: hits,
      }),
    [query, commandMode, hits],
  )

  const flatItems = useMemo(() => flattenGroups(groups), [groups])

  useEffect(() => {
    if (!open) {
      setQuery('')
      setActiveId(null)
      searchTracked.current = false
      return
    }
    setRecent(getRecentSearches())
  }, [open])

  useEffect(() => {
    if (!flatItems.length) {
      setActiveId(null)
      return
    }
    if (!activeId || !flatItems.some((i) => i.id === activeId)) {
      setActiveId(flatItems[0].id)
    }
  }, [flatItems, activeId])

  useEffect(() => {
    if (!open || commandMode.active) {
      searchTracked.current = false
      return
    }
    const q = query.trim()
    if (q.length < 2) {
      searchTracked.current = false
      return
    }
    if (searchTracked.current) return
    searchTracked.current = true
    try {
      trackProductEvent('command_center.search', {
        queryLength: q.length,
        commandMode: false,
      })
    } catch {
      /* ignore */
    }
  }, [open, query, commandMode.active])

  const itemDomId = useCallback(
    (itemId: string) => `cc-option-${itemId.replace(/[^a-zA-Z0-9_-]/g, '_')}`,
    [],
  )

  const handleSelect = useCallback(
    (item: CommandResultItem) => {
      if (query.trim() && !commandMode.active) {
        setRecent(pushRecentSearch(query.trim()))
      }
      try {
        trackProductEvent('command_center.navigate', {
          kind: item.kind,
          group: item.group,
          href: item.href,
        })
      } catch {
        /* ignore */
      }
      onNavigate(item.href, { kind: item.kind, title: item.title })
    },
    [query, commandMode.active, onNavigate],
  )

  const openFullSearch = useCallback(() => {
    const href = searchPageHref(commandMode.active ? '' : query)
    if (query.trim() && !commandMode.active) setRecent(pushRecentSearch(query.trim()))
    try {
      trackProductEvent('command_center.navigate', { kind: 'search_page', href })
    } catch {
      /* ignore */
    }
    onNavigate(href)
  }, [query, commandMode.active, onNavigate])

  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        if (!flatItems.length) return
        const idx = flatItems.findIndex((i) => i.id === activeId)
        const next = flatItems[(idx + 1) % flatItems.length]
        setActiveId(next.id)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        if (!flatItems.length) return
        const idx = flatItems.findIndex((i) => i.id === activeId)
        const next = flatItems[(idx - 1 + flatItems.length) % flatItems.length]
        setActiveId(next.id)
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        const item = flatItems.find((i) => i.id === activeId) || flatItems[0]
        if (item) handleSelect(item)
        else if (query.trim() && !commandMode.active) openFullSearch()
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    },
    [flatItems, activeId, handleSelect, query, commandMode.active, openFullSearch, onClose],
  )

  const showIdleExtras = !query.trim() && !commandMode.active

  return (
    <div
      className={cx('cc-panel', 'cc-panel--signature', embedded && 'cc-panel--embedded')}
      id={panelId}
    >
      <CommandCenterHeader titleId={titleId} descriptionId={descId} embedded={embedded} />
      <div className="cc-body">
        <CommandInput
          ref={resolvedInputRef}
          id={inputId}
          value={query}
          onChange={setQuery}
          onKeyDown={onKeyDown}
          commandMode={commandMode.active}
        />

        {showIdleExtras ? (
          <>
            <RecentSearches
              items={recent}
              onSelect={setQuery}
              onClear={() => {
                clearRecentSearches()
                setRecent([])
              }}
            />
            <div className="cc-idle-hint">
              <p className="cc-idle-hint__text">
                Tapez pour rechercher, ou <kbd>&gt;</kbd> pour une commande.
              </p>
            </div>
          </>
        ) : null}

        <CommandResults
          groups={groups}
          flatItems={flatItems}
          activeId={activeId}
          status={commandMode.active ? 'ready' : status}
          errorMessage={errorMessage}
          query={commandMode.active ? commandMode.commandText : query}
          commandMode={commandMode.active}
          itemDomId={itemDomId}
          onSelect={handleSelect}
          onHover={setActiveId}
          onRetry={() => setRetryKey((k) => k + 1)}
          onOpenFullSearch={openFullSearch}
        />
      </div>
      <SearchFooter
        showFullSearch={!commandMode.active && query.trim().length > 0}
        onOpenFullSearch={openFullSearch}
      />
    </div>
  )
}
