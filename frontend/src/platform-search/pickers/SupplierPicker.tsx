/**
 * SupplierPicker — Relations filtrées rôle supplier.
 */

import type { ReactNode } from 'react'
import type { SearchResult } from '../types'
import { RelationPicker } from './RelationPicker'

export type SupplierPickerProps = {
  onSelect: (item: SearchResult) => void
  selected?: SearchResult | null
  selectedSlot?: ReactNode
  className?: string
}

export function SupplierPicker({ onSelect, selected, selectedSlot, className }: SupplierPickerProps) {
  return (
    <RelationPicker
      role="supplier"
      className={className}
      label="Fournisseur"
      placeholder="Rechercher un fournisseur…"
      onSelect={onSelect}
      selected={selected}
      selectedSlot={selectedSlot}
      openRelationsHref="/platform/relations?tab=supplier"
    />
  )
}
