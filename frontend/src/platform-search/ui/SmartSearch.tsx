/**
 * SmartSearch — combobox a11y, résultats groupés, debounce via useSmartSearch.
 * N’enregistre PAS Cmd/Ctrl+K (réservé Command Center).
 */

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { useSmartSearch, type UseSmartSearchOptions } from '../hooks/useSmartSearch'
import { handleListKeyboard } from '../keyboard'
import type { SearchResult } from '../types'
import { SmartSearchGroupView, SmartSearchStatusView } from './SmartSearchParts'
import './platform-search.css'

export type SmartSearchProps = {
  value?: string
  onQueryChange?: (q: string) => void
  onSelect: (item: SearchResult) => void
  placeholder?: string
  label?: string
  emptyLabel?: string
  className?: string
  autoFocus?: boolean
  searchOptions?: UseSmartSearchOptions
  /** Affiche le panneau même sans focus (pickers wizard). */
  alwaysOpen?: boolean
}

export function SmartSearch({
  value,
  onQueryChange,
  onSelect,
  placeholder = 'Rechercher…',
  label = 'Recherche',
  emptyLabel,
  className,
  autoFocus,
  searchOptions,
  alwaysOpen = false,
}: SmartSearchProps) {
  const reactId = useId()
  const listboxId = `${reactId}-listbox`
  const inputId = `${reactId}-input`
  const [internalQ, setInternalQ] = useState(value ?? '')
  const q = value !== undefined ? value : internalQ
  const [open, setOpen] = useState(alwaysOpen)
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)

  const { status, errorMessage, items, groups } = useSmartSearch(q, {
    minChars: 2,
    ...searchOptions,
  })

  const flatItems = useMemo(() => {
    if (groups.length) return groups.flatMap((g) => g.items)
    return items
  }, [groups, items])

  useEffect(() => {
    setActiveIndex(0)
  }, [flatItems.length, q])

  useEffect(() => {
    if (alwaysOpen) return
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    return () => document.removeEventListener('pointerdown', onPointer)
  }, [alwaysOpen])

  const setQ = (next: string) => {
    if (value === undefined) setInternalQ(next)
    onQueryChange?.(next)
    setOpen(true)
  }

  const optionId = (index: number) => `${reactId}-opt-${index}`

  const selectIndex = (index: number) => {
    const item = flatItems[index]
    if (!item) return
    onSelect(item)
    setOpen(false)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    handleListKeyboard(e, {
      itemCount: flatItems.length,
      activeIndex,
      setActiveIndex,
      onSelect: selectIndex,
      onEscape: () => setOpen(false),
    })
  }

  const showPanel = alwaysOpen || open
  const showList =
    showPanel && (status === 'ready' || status === 'partial') && flatItems.length > 0

  let offset = 0

  return (
    <div className={`ps-search ${className ?? ''}`.trim()} ref={rootRef} data-platform-search="v1">
      <div className="ps-search__input-wrap">
        <input
          id={inputId}
          className="ps-search__input"
          type="search"
          role="combobox"
          aria-label={label}
          aria-expanded={showPanel}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            showList && flatItems[activeIndex] ? optionId(activeIndex) : undefined
          }
          placeholder={placeholder}
          value={q}
          autoFocus={autoFocus}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
      </div>

      {showPanel ? (
        <div className="ps-search__panel" id={listboxId} role="listbox" aria-label={label}>
          {showList
            ? groups.length
              ? groups.map((group) => {
                  const view = (
                    <SmartSearchGroupView
                      key={group.id}
                      group={group}
                      flatOffset={offset}
                      activeIndex={activeIndex}
                      optionId={optionId}
                      onSelectIndex={selectIndex}
                      setActiveIndex={setActiveIndex}
                    />
                  )
                  offset += group.items.length
                  return view
                })
              : flatItems.map((item, index) => (
                  <SmartSearchGroupView
                    key={`${item.id}-${index}`}
                    group={{ id: 'all', label: 'Résultats', items: [item] }}
                    flatOffset={index}
                    activeIndex={activeIndex}
                    optionId={optionId}
                    onSelectIndex={selectIndex}
                    setActiveIndex={setActiveIndex}
                  />
                ))
            : (
                <SmartSearchStatusView
                  status={status}
                  errorMessage={errorMessage}
                  emptyLabel={emptyLabel}
                />
              )}
        </div>
      ) : null}
    </div>
  )
}
