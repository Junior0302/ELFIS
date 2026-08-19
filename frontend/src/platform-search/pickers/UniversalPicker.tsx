/**
 * Universal Picker framework — utilise Smart Search (pas son propre moteur).
 */

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { SmartSearch } from '../ui/SmartSearch'
import type { UseSmartSearchOptions } from '../hooks/useSmartSearch'
import type { SearchResult } from '../types'
import '../ui/platform-search.css'

export type UniversalPickerCreateAction = {
  label: string
  onClick: () => void
  disabled?: boolean
}

export type UniversalPickerProps = {
  label: string
  placeholder?: string
  emptyLabel?: string
  onSelect: (item: SearchResult) => void
  searchOptions: UseSmartSearchOptions
  query?: string
  onQueryChange?: (q: string) => void
  selected?: SearchResult | null
  selectedSlot?: ReactNode
  createAction?: UniversalPickerCreateAction
  /** Navigation legacy — préférer `onOpen` dans le Composer (évite nouvel onglet / sortie modal). */
  openHref?: string
  /** Ouvre une surface interne (drawer) sans navigation. */
  onOpen?: () => void
  openLabel?: string
  alwaysOpen?: boolean
  footer?: ReactNode
  className?: string
}

export function UniversalPicker({
  label,
  placeholder,
  emptyLabel,
  onSelect,
  searchOptions,
  query,
  onQueryChange,
  selected,
  selectedSlot,
  createAction,
  openHref,
  onOpen,
  openLabel = 'Ouvrir',
  alwaysOpen = false,
  footer,
  className,
}: UniversalPickerProps) {
  return (
    <div className={`ps-picker ${className ?? ''}`.trim()} data-universal-picker="v1">
      <SmartSearch
        label={label}
        placeholder={placeholder}
        emptyLabel={emptyLabel}
        value={query}
        onQueryChange={onQueryChange}
        onSelect={onSelect}
        searchOptions={{
          allowEmptyQuery: false,
          minChars: 1,
          ...searchOptions,
        }}
        alwaysOpen={alwaysOpen}
      />

      <div className="ps-picker__actions">
        {createAction ? (
          <button
            type="button"
            className="btn secondary"
            disabled={createAction.disabled}
            onClick={createAction.onClick}
          >
            {createAction.label}
          </button>
        ) : null}
        {onOpen ? (
          <button type="button" className="btn" onClick={onOpen}>
            {openLabel}
          </button>
        ) : openHref ? (
          <Link className="btn secondary" to={openHref} target="_blank" rel="noreferrer">
            {openLabel}
          </Link>
        ) : null}
      </div>

      {selectedSlot
        ? selectedSlot
        : selected ? (
            <div className="ps-picker__selected" role="status">
              <strong>{selected.title}</strong>
              {selected.subtitle ? <p className="ps-picker__meta">{selected.subtitle}</p> : null}
            </div>
          ) : null}

      {footer}
    </div>
  )
}
