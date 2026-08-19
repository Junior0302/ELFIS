import type { ResourceSort, ResourceStatus } from '../types'
import type { SmartLibraryFilters } from '../hooks/useResourceLibrary'

export type SmartFiltersProps = {
  filters: SmartLibraryFilters
  onChange: (patch: Partial<SmartLibraryFilters>) => void
  view: 'cards' | 'list'
  onViewChange: (view: 'cards' | 'list') => void
  vatOptions: number[]
}

export function SmartFilters({
  filters,
  onChange,
  view,
  onViewChange,
  vatOptions,
}: SmartFiltersProps) {
  const vatList = vatOptions.length ? vatOptions : [0, 5.5, 10, 20]

  return (
    <div className="sl-filters">
      <div className="sl-filters__row">
        <input
          type="search"
          placeholder="Rechercher (Smart Search local)…"
          value={filters.q}
          onChange={(e) => onChange({ q: e.target.value })}
          aria-label="Recherche bibliothèque"
        />
        <div className="sl-view-toggle" role="group" aria-label="Mode d’affichage">
          <button
            type="button"
            className={view === 'cards' ? 'is-active' : undefined}
            onClick={() => onViewChange('cards')}
          >
            Cartes
          </button>
          <button
            type="button"
            className={view === 'list' ? 'is-active' : undefined}
            onClick={() => onViewChange('list')}
          >
            Liste
          </button>
        </div>
      </div>
      <div className="sl-filters__row">
        <select
          aria-label="Filtrer par type"
          value={filters.kinds[0] ?? ''}
          onChange={(e) => {
            const v = e.target.value
            onChange({
              kinds: v ? [v as 'product' | 'service'] : [],
            })
          }}
        >
          <option value="">Type — tous</option>
          <option value="product">Produits</option>
          <option value="service">Services</option>
        </select>
        <select
          aria-label="Filtrer par TVA"
          value={filters.vatRates[0] ?? ''}
          onChange={(e) => {
            const v = e.target.value
            onChange({ vatRates: v === '' ? [] : [Number(v)] })
          }}
        >
          <option value="">TVA — toutes</option>
          {vatList.map((rate) => (
            <option key={rate} value={rate}>
              {rate} %
            </option>
          ))}
        </select>
        <select
          aria-label="Statut"
          value={filters.status}
          onChange={(e) => onChange({ status: e.target.value as ResourceStatus | 'any' })}
        >
          <option value="any">Statut — tous</option>
          <option value="active">Actifs</option>
          <option value="inactive">Inactifs</option>
        </select>
        <input
          type="number"
          min={0}
          step="0.01"
          placeholder="Prix min HT"
          value={filters.priceMin ?? ''}
          onChange={(e) =>
            onChange({ priceMin: e.target.value === '' ? null : Number(e.target.value) })
          }
          aria-label="Prix minimum HT"
        />
        <input
          type="number"
          min={0}
          step="0.01"
          placeholder="Prix max HT"
          value={filters.priceMax ?? ''}
          onChange={(e) =>
            onChange({ priceMax: e.target.value === '' ? null : Number(e.target.value) })
          }
          aria-label="Prix maximum HT"
        />
        <select
          aria-label="Tri"
          value={filters.sort}
          onChange={(e) => onChange({ sort: e.target.value as ResourceSort })}
        >
          <option value="name_asc">Nom A→Z</option>
          <option value="name_desc">Nom Z→A</option>
          <option value="price_asc">Prix croissant</option>
          <option value="price_desc">Prix décroissant</option>
          <option value="updated_desc">Récemment mis à jour</option>
        </select>
        <label className="checkbox-inline" style={{ color: 'inherit', fontSize: '0.85rem' }}>
          <input
            type="checkbox"
            checked={filters.activeOnly}
            onChange={(e) => onChange({ activeOnly: e.target.checked })}
          />
          Actifs seulement
        </label>
      </div>
      <p className="sl-status" style={{ margin: 0 }}>
        Catégorie : non exposée par l’API catalogue V1 — filtre masqué.
      </p>
    </div>
  )
}
