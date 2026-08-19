import type { CommandResultItem } from './commandTypes'

export type QuickActionsProps = {
  items: CommandResultItem[]
  onSelect: (item: CommandResultItem) => void
}

/** Idle / keyword strip — optional compact chips when parent passes filtered items. */
export function QuickActions({ items, onSelect }: QuickActionsProps) {
  if (!items.length) return null
  return (
    <div className="cc-quick" aria-label="Commandes rapides">
      <p className="cc-quick__label">Suggestions</p>
      <ul className="cc-quick__list">
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" className="cc-quick__chip" onClick={() => onSelect(item)}>
              {item.title}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
