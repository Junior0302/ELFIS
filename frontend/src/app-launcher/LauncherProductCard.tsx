import type { CSSProperties, KeyboardEvent } from 'react'

import { Link } from 'react-router-dom'

import type { ResolvedSpace } from './spaces.types'

import { cx } from '../design-system/components/cx'
import { WorkspaceSpaceIcon } from '../workspaces/WorkspaceSpaceIcon'



export type LauncherProductCardProps = {

  item: ResolvedSpace

  onSelect?: (item: ResolvedSpace) => void

  onUnavailableClick?: (item: ResolvedSpace) => void

  variant?: 'available' | 'coming_soon'

  onNavigateAway?: () => void

}



/**

 * Carte espace métier commune — accent domaine, raccourcis, signature moteur.

 */

export function LauncherProductCard({

  item,

  onSelect,

  onUnavailableClick,

  variant = 'available',

  onNavigateAway,

}: LauncherProductCardProps) {

  const { space, state } = item

  const comingSoon = state === 'coming_soon' || variant === 'coming_soon'

  const locked = state === 'locked' || state === 'unavailable'

  const disabled = comingSoon || locked

  const style = {

    '--launcher-card-accent': space.accent,

  } as CSSProperties



  const onActivate = () => {

    if (disabled) {

      onUnavailableClick?.(item)

      return

    }

    onSelect?.(item)

  }



  const onKeyDown = (e: KeyboardEvent) => {

    if (e.key === 'Enter' || e.key === ' ') {

      e.preventDefault()

      onActivate()

    }

  }



  const statusText =

    state === 'coming_soon'

      ? 'Bientôt'

      : state === 'active'

        ? 'Espace actif'

        : state === 'beta'

          ? 'Bêta'

          : state === 'locked'

            ? item.label

            : state === 'unavailable'

              ? 'Indisponible'

              : null



  const shortcuts = space.shortcuts.slice(0, 3)



  const body = (

    <>

      <div className="launcher-card__top">

        <WorkspaceSpaceIcon
          icon={space.icon}
          accent={space.accent}
          soft={space.accentSoft}
          className="launcher-card__mark"
        />

        <span className="launcher-card__identity">

          <span className="launcher-card__title-row">

            <span className="launcher-card__title">{space.title}</span>

            {statusText ? (

              <span className={cx('launcher-card__badge', `launcher-card__badge--${state}`)}>

                {statusText}

              </span>

            ) : null}

            {item.isLastUsed ? (

              <span className="launcher-card__badge launcher-card__badge--last">Dernière visite</span>

            ) : null}

          </span>

          {space.engineLabel ? (

            <span className="launcher-card__engine">{space.engineLabel}</span>

          ) : null}

        </span>

      </div>

      <p className="launcher-card__desc">{space.description}</p>

      {shortcuts.length > 0 && !comingSoon ? (

        <ul className="launcher-card__caps" aria-label="Raccourcis">

          {shortcuts.map((sc) => (

            <li key={sc.id}>

              <Link

                to={sc.to}

                className="launcher-card__shortcut"

                onClick={(e) => {

                  e.stopPropagation()

                  onNavigateAway?.()

                }}

              >

                {sc.label}

              </Link>

            </li>

          ))}

        </ul>

      ) : space.capabilities.length > 0 ? (

        <ul className="launcher-card__caps" aria-label="Fonctions">

          {space.capabilities.slice(0, 3).map((cap) => (

            <li key={cap}>{cap}</li>

          ))}

        </ul>

      ) : null}

      {!disabled ? (

        <span className="launcher-card__action" aria-hidden>

          {state === 'active' ? 'Ouvert' : `Ouvrir ${space.title}`}

        </span>

      ) : comingSoon ? (

        <span className="launcher-card__action launcher-card__action--muted" aria-hidden>

          Bientôt

        </span>

      ) : null}

    </>

  )



  if (disabled) {

    return (

      <div

        className={cx(

          'launcher-card',

          'launcher-card--disabled',

          comingSoon && 'launcher-card--soon',

        )}

        style={style}

        aria-disabled="true"

        data-state={state}

        data-space={space.id}

        role="button"

        tabIndex={0}

        onClick={onActivate}

        onKeyDown={onKeyDown}

        aria-label={`${space.title}, ${statusText ?? 'indisponible'}`}

      >

        {body}

      </div>

    )

  }



  return (

    <button

      type="button"

      className={cx('launcher-card', state === 'active' && 'launcher-card--active')}

      style={style}

      data-state={state}

      data-space={space.id}

      onClick={onActivate}

      onKeyDown={onKeyDown}

      aria-current={state === 'active' ? 'true' : undefined}

      aria-label={

        state === 'active' ? `${space.title}, espace actif` : `Ouvrir ${space.title}`

      }

    >

      {body}

    </button>

  )

}



/** @deprecated Prefer LauncherProductCard — kept for sandbox / legacy imports. */

export { LauncherProductCard as AppLauncherProductCard }


