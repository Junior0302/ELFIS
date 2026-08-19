export type RecentSearchesProps = {
  items: string[]
  onSelect: (query: string) => void
  onClear: () => void
}

export function RecentSearches({ items, onSelect, onClear }: RecentSearchesProps) {
  if (!items.length) return null
  return (
    <div className="cc-recent" aria-label="Recherches récentes">
      <div className="cc-recent__head">
        <p className="cc-recent__label">Récentes</p>
        <button type="button" className="cc-recent__clear" onClick={onClear}>
          Effacer
        </button>
      </div>
      <ul className="cc-recent__list">
        {items.map((q) => (
          <li key={q}>
            <button type="button" className="cc-recent__item" onClick={() => onSelect(q)}>
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
