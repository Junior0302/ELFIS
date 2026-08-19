import type { CommandResultGroup, CommandResultItem } from './commandTypes'
import { ResultItem } from './ResultItem'

export type ResultGroupProps = {
  group: CommandResultGroup
  activeId: string | null
  itemDomId: (itemId: string) => string
  onSelect: (item: CommandResultItem) => void
  onHover: (itemId: string) => void
}

export function ResultGroup({ group, activeId, itemDomId, onSelect, onHover }: ResultGroupProps) {
  return (
    <section className="cc-group" aria-labelledby={`cc-group-${group.id}`}>
      <h3 id={`cc-group-${group.id}`} className="cc-group__title">
        {group.label}
      </h3>
      <ul className="cc-group__list" role="presentation">
        {group.items.map((item) => (
          <ResultItem
            key={item.id}
            item={item}
            id={itemDomId(item.id)}
            active={activeId === item.id}
            onSelect={onSelect}
            onHover={() => onHover(item.id)}
          />
        ))}
      </ul>
    </section>
  )
}
