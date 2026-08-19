/**
 * RelationPicker — SharedRelation (recherche, sélection, créer si autorisé, ouvrir Relations).
 * Récents désactivés (pas de source métier permanente).
 */

import { useState, type ReactNode } from 'react'
import type { SearchResult } from '../types'
import { DISABLED_RECENTS } from '../sources/smartSearchSources'
import { UniversalPicker } from './UniversalPicker'

export type RelationPickerProps = {
  role?: 'customer' | 'supplier' | string
  onSelect: (item: SearchResult) => void
  selected?: SearchResult | null
  selectedSlot?: ReactNode
  createAction?: { label: string; onClick: () => void; disabled?: boolean }
  openRelationsHref?: string
  label?: string
  placeholder?: string
  className?: string
  footer?: ReactNode
}

export function RelationPicker({
  role,
  onSelect,
  selected,
  selectedSlot,
  createAction,
  openRelationsHref = role
    ? `/platform/relations?tab=${encodeURIComponent(role)}`
    : '/platform/relations',
  label = 'Relation',
  placeholder = 'Rechercher une relation…',
  className,
  footer,
}: RelationPickerProps) {
  const [q, setQ] = useState('')
  const scope =
    role === 'customer' ? 'customers' : role === 'supplier' ? 'suppliers' : 'relations'

  return (
    <UniversalPicker
      className={className}
      label={label}
      placeholder={placeholder}
      emptyLabel={
        DISABLED_RECENTS.enabled
          ? 'Aucun résultat'
          : 'Aucune relation trouvée. Ouvrez ELFIS Relations pour enrichir l’annuaire.'
      }
      query={q}
      onQueryChange={setQ}
      onSelect={onSelect}
      selected={selected}
      selectedSlot={selectedSlot}
      createAction={createAction}
      openHref={openRelationsHref}
      openLabel="Ouvrir ELFIS Relations"
      searchOptions={{
        scope,
        allowEmptyQuery: false,
        minChars: 1,
        pageSize: 20,
      }}
      footer={footer}
    />
  )
}
