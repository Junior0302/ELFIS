import type { CommandResultItem } from './commandTypes'
import { cx } from '../design-system/components/cx'

export type ResultItemProps = {
  item: CommandResultItem
  active: boolean
  id: string
  onSelect: (item: CommandResultItem) => void
  onHover: () => void
}

export function ResultItem({ item, active, id, onSelect, onHover }: ResultItemProps) {
  return (
    <li id={id} role="option" aria-selected={active}>
      <button
        type="button"
        className={cx('cc-result', active && 'cc-result--active')}
        onClick={() => onSelect(item)}
        onMouseEnter={onHover}
      >
        <span className="cc-result__title">{item.title}</span>
        {item.subtitle ? <span className="cc-result__sub">{item.subtitle}</span> : null}
      </button>
    </li>
  )
}
