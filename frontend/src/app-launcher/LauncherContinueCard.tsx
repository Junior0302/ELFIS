import type { CSSProperties } from 'react'

import type { ResolvedSpace } from './spaces.types'

import { formatSpaceActivity } from './spacesModel'

import { cx } from '../design-system/components/cx'



export type LauncherContinueCardProps = {

  item: ResolvedSpace

  onSelect: (item: ResolvedSpace) => void

  /** True when showing fallback Finance (no lastProduct). */

  isFallback?: boolean

}



export function LauncherContinueCard({ item, onSelect, isFallback = false }: LauncherContinueCardProps) {

  const { space, state, canOpen, lastActivityAt } = item

  const style = {

    '--launcher-card-accent': space.accent,

  } as CSSProperties



  const interactive = canOpen || state === 'active'

  const title = isFallback

    ? `Commencer dans ${space.title}`

    : `Reprendre dans ${space.title}`



  const activity = !isFallback ? formatSpaceActivity(lastActivityAt) : null

  const metaParts = [

    !isFallback && space.engineLabel ? space.engineLabel : null,

    activity,

    state === 'active' ? 'Espace actif' : null,

  ].filter(Boolean)



  return (

    <button

      type="button"

      className={cx(

        'launcher-continue',

        state === 'active' && 'launcher-continue--active',

        !interactive && 'launcher-continue--disabled',

      )}

      style={style}

      disabled={!interactive}

      onClick={() => {

        if (interactive) onSelect(item)

      }}

      aria-label={title}

    >

      <span

        className="launcher-continue__mark"

        style={{ background: `color-mix(in srgb, ${space.accent} 18%, transparent)`, color: space.accent }}

        aria-hidden

      >

        {space.title.slice(0, 1)}

      </span>

      <span className="launcher-continue__body">

        <span className="launcher-continue__eyebrow">{isFallback ? 'Commencer' : 'Reprendre'}</span>

        <span className="launcher-continue__title">{title}</span>

        <span className="launcher-continue__desc">

          {metaParts.length > 0 ? metaParts.join(' · ') : space.description}

        </span>

      </span>

      <span className="launcher-continue__cta" aria-hidden>

        {state === 'active' ? 'Ouvert' : 'Ouvrir'}

      </span>

    </button>

  )

}


