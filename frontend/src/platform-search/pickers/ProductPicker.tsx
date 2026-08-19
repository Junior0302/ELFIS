/**
 * ProductPicker — catalogue local via ProductSource / Resource System.
 */

import { useState, type ReactNode } from 'react'
import type { SearchResult } from '../types'
import { resolveProductSource, type ProductSourceId } from '../sources/productSource'
import { UniversalPicker } from './UniversalPicker'

export type ProductPickerProps = {
  onSelect: (item: SearchResult) => void
  selected?: SearchResult | null
  preferredSource?: ProductSourceId
  createAction?: { label: string; onClick: () => void; disabled?: boolean }
  /** Legacy : lien catalogue. Préférer `onOpenCatalog` dans le Composer modal. */
  openCatalogHref?: string
  /** Ouvre le drawer catalogue interne (pas de navigation). */
  onOpenCatalog?: () => void
  openCatalogLabel?: string
  className?: string
  footer?: ReactNode
}

export function ProductPicker({
  onSelect,
  selected,
  preferredSource = 'local_catalog',
  createAction,
  openCatalogHref,
  onOpenCatalog,
  openCatalogLabel = 'Parcourir le catalogue',
  className,
  footer,
}: ProductPickerProps) {
  const [q, setQ] = useState('')
  const source = resolveProductSource(preferredSource)

  return (
    <div className={className}>
      <UniversalPicker
        label="Produit"
        placeholder="Rechercher un produit…"
        emptyLabel={
          source.available
            ? 'Aucun produit dans le catalogue.'
            : 'Aucune source catalogue disponible.'
        }
        query={q}
        onQueryChange={setQ}
        onSelect={onSelect}
        selected={selected}
        createAction={createAction}
        onOpen={onOpenCatalog}
        openHref={onOpenCatalog ? undefined : openCatalogHref}
        openLabel={openCatalogLabel}
        searchOptions={{
          scope: 'products',
          allowEmptyQuery: false,
          minChars: 1,
          pageSize: 40,
        }}
        footer={footer}
      />
    </div>
  )
}

/** Helper Composer : SearchResult catalogue → champs ligne. */
export function catalogResultToLineFields(item: SearchResult): {
  catalogItemId: number | null
  label: string
  unitPrice: number
  vatRate: number
  catalogCreatedAt?: string
} {
  const meta = item.metadata ?? {}
  const createdAt =
    typeof meta.created_at === 'string'
      ? meta.created_at
      : typeof meta.createdAt === 'string'
        ? meta.createdAt
        : undefined
  return {
    catalogItemId: typeof meta.catalogItemId === 'number' ? meta.catalogItemId : Number(item.id) || null,
    label: item.title,
    unitPrice: typeof meta.unit_price_ht === 'number' ? meta.unit_price_ht : 0,
    vatRate: typeof meta.vat_rate === 'number' ? meta.vat_rate : 20,
    ...(createdAt ? { catalogCreatedAt: createdAt } : {}),
  }
}
