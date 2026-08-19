/**
 * DocumentPicker — facture / devis / avoir via billingOverview (sources existantes).
 * Option Search Engine V1 pour vault / documents indexés.
 */

import { useState } from 'react'
import type { SearchEntityType, SearchResult } from '../types'
import { UniversalPicker } from './UniversalPicker'

export type DocumentPickerProps = {
  onSelect: (item: SearchResult) => void
  selected?: SearchResult | null
  /** Filtre types Smart Search (invoice | quote | credit_note | document). */
  types?: SearchEntityType[]
  /** Si true, utilise Search Engine V1 (vault / indexed) au lieu du billing overview. */
  useSearchEngine?: boolean
  className?: string
}

export function DocumentPicker({
  onSelect,
  selected,
  types,
  useSearchEngine = false,
  className,
}: DocumentPickerProps) {
  const [q, setQ] = useState('')

  return (
    <UniversalPicker
      className={className}
      label="Document"
      placeholder="Rechercher un document…"
      emptyLabel="Aucun document trouvé pour ces critères."
      query={q}
      onQueryChange={setQ}
      onSelect={onSelect}
      selected={selected}
      openHref="/facturation"
      openLabel="Ouvrir Facturation"
      alwaysOpen
      searchOptions={{
        scope: useSearchEngine ? 'global' : 'documents',
        types: useSearchEngine
          ? types ?? ['vault_document', 'document', 'accounting_entry']
          : types ?? ['invoice', 'quote', 'credit_note', 'document'],
        allowEmptyQuery: true,
        minChars: useSearchEngine ? 2 : 0,
        pageSize: 30,
      }}
    />
  )
}
