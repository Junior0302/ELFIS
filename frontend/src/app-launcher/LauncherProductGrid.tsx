import type { ResolvedSpace } from './spaces.types'

import { LauncherProductCard } from './LauncherProductCard'



export type LauncherProductGridProps = {

  items: ResolvedSpace[]

  onSelect?: (item: ResolvedSpace) => void

  onUnavailableClick?: (item: ResolvedSpace) => void

  variant?: 'available' | 'coming_soon'

  labelledBy: string

  emptyMessage?: string | null

  onNavigateAway?: () => void

}



export function LauncherProductGrid({

  items,

  onSelect,

  onUnavailableClick,

  variant = 'available',

  labelledBy,

  emptyMessage,

  onNavigateAway,

}: LauncherProductGridProps) {

  if (items.length === 0) {

    return emptyMessage ? <p className="app-launcher-panel__empty">{emptyMessage}</p> : null

  }



  return (

    <ul className="launcher-grid" aria-labelledby={labelledBy}>

      {items.map((item) => (

        <li key={item.space.id}>

          <LauncherProductCard

            item={item}

            onSelect={onSelect}

            onUnavailableClick={onUnavailableClick}

            variant={variant}

            onNavigateAway={onNavigateAway}

          />

        </li>

      ))}

    </ul>

  )

}


