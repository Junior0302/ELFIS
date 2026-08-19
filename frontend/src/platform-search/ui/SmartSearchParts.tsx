import type { SearchGroup, SearchResult, SmartSearchStatus } from '../types'

export function SmartSearchStatusView({
  status,
  errorMessage,
  emptyLabel = 'Aucun résultat',
}: {
  status: SmartSearchStatus
  errorMessage?: string | null
  emptyLabel?: string
}) {
  if (status === 'idle') {
    return <div className="ps-search__status">Saisissez au moins 2 caractères…</div>
  }
  if (status === 'typing' || status === 'loading') {
    return <div className="ps-search__status">Recherche…</div>
  }
  if (status === 'offline') {
    return <div className="ps-search__status ps-search__status--error">Hors ligne</div>
  }
  if (status === 'error') {
    return (
      <div className="ps-search__status ps-search__status--error" role="alert">
        {errorMessage || 'Erreur de recherche'}
      </div>
    )
  }
  if (status === 'empty') {
    return <div className="ps-search__status">{emptyLabel}</div>
  }
  if (status === 'partial') {
    return (
      <div className="ps-search__status" role="status">
        Résultats partiels — une source a échoué.
      </div>
    )
  }
  return null
}

export function SmartSearchItem({
  item,
  active,
  id,
  onSelect,
  onMouseEnter,
}: {
  item: SearchResult
  active: boolean
  id: string
  onSelect: () => void
  onMouseEnter: () => void
}) {
  return (
    <button
      type="button"
      id={id}
      role="option"
      aria-selected={active}
      className="ps-search__item"
      onClick={onSelect}
      onMouseEnter={onMouseEnter}
    >
      <span className="ps-search__item-title">{item.title}</span>
      {item.subtitle ? <span className="ps-search__item-sub">{item.subtitle}</span> : null}
      {item.description ? <span className="ps-search__item-sub">{item.description}</span> : null}
    </button>
  )
}

export function SmartSearchGroupView({
  group,
  flatOffset,
  activeIndex,
  optionId,
  onSelectIndex,
  setActiveIndex,
}: {
  group: SearchGroup
  flatOffset: number
  activeIndex: number
  optionId: (index: number) => string
  onSelectIndex: (index: number) => void
  setActiveIndex: (index: number) => void
}) {
  return (
    <div role="group" aria-label={group.label}>
      <div className="ps-search__group-label">{group.label}</div>
      {group.items.map((item, i) => {
        const index = flatOffset + i
        return (
          <SmartSearchItem
            key={`${item.source}-${item.id}-${index}`}
            item={item}
            id={optionId(index)}
            active={activeIndex === index}
            onSelect={() => onSelectIndex(index)}
            onMouseEnter={() => setActiveIndex(index)}
          />
        )
      })}
    </div>
  )
}
