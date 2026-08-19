import { useEffect, useId, useMemo, useRef, useState, type RefObject } from 'react'

import type { LauncherResolveContext } from './launcher.types'

import type { ResolvedSpace, SpaceSections } from './spaces.types'

import {

  buildSpaceSections,

  collectAllSpaces,

  filterSpaces,

  resolveContinueSpace,

} from './spacesModel'

import { LauncherHeader } from './LauncherHeader'

import { LauncherSearch } from './LauncherSearch'

import { LauncherContinueCard } from './LauncherContinueCard'

import { LauncherProductGrid } from './LauncherProductGrid'

import { LauncherFooter } from './LauncherFooter'

import { cx } from '../design-system/components/cx'

import { trackProductEvent } from '../productEvents'



export type AppLauncherPanelProps = {

  /** @deprecated Prefer resolveContext — sections rebuilt from spaces catalog. */

  sections?: SpaceSections

  resolveContext: LauncherResolveContext

  onSelect: (item: ResolvedSpace) => void

  onUnavailableClick?: (item: ResolvedSpace) => void

  errorMessage?: string | null

  panelId?: string

  onNavigateAway?: () => void

  /** Header allégé (Drawer mobile déjà titré) */

  embedded?: boolean

  searchInputRef?: RefObject<HTMLInputElement | null>

}



export function AppLauncherPanel({

  sections: sectionsProp,

  resolveContext,

  onSelect,

  onUnavailableClick,

  errorMessage,

  panelId,

  onNavigateAway,

  embedded = false,

  searchInputRef,

}: AppLauncherPanelProps) {

  const [query, setQuery] = useState('')

  const titleId = useId()

  const descId = useId()

  const searchTracked = useRef(false)



  const sections = useMemo(

    () => sectionsProp ?? buildSpaceSections(resolveContext),

    [sectionsProp, resolveContext],

  )



  const { continueItem, fallbackContinue } = useMemo(

    () => resolveContinueSpace(sections, resolveContext),

    [sections, resolveContext],

  )



  const allSearchable = useMemo(() => collectAllSpaces(sections), [sections])



  const q = query.trim()

  const filtering = q.length > 0



  const filteredAll = useMemo(

    () => (filtering ? filterSpaces(allSearchable, q) : null),

    [filtering, allSearchable, q],

  )



  const availableItems = filtering

    ? (filteredAll ?? []).filter(

        (i) =>

          i.state === 'active' ||

          i.state === 'available' ||

          i.state === 'beta' ||

          i.state === 'locked',

      )

    : sections.available



  const soonItems = filtering

    ? (filteredAll ?? []).filter((i) => i.state === 'coming_soon' || i.state === 'unavailable')

    : sections.comingSoon



  useEffect(() => {

    if (!filtering || searchTracked.current) return

    searchTracked.current = true

    try {

      trackProductEvent('app_launcher.searched', {

        resultCount: filteredAll?.length ?? 0,

      })

    } catch {

      /* ignore */

    }

  }, [filtering, filteredAll?.length])



  useEffect(() => {

    if (!filtering) searchTracked.current = false

  }, [filtering])



  const showContinue = !filtering && (continueItem || fallbackContinue)

  const emptySearch = filtering && (filteredAll?.length ?? 0) === 0



  return (

    <div

      id={panelId}

      className={cx(

        'app-launcher-panel',

        'app-launcher-panel--premium',

        'app-launcher-panel--signature',

        embedded && 'app-launcher-panel--embedded',

      )}

      data-launcher="spaces-hub-v1"

      aria-labelledby={titleId}

      aria-describedby={descId}

    >

      <LauncherHeader

        titleId={titleId}

        descriptionId={descId}

        embedded={embedded}

        onNavigateAway={onNavigateAway}

      />



      <div className="launcher-toolbar">

        <LauncherSearch value={query} onChange={setQuery} inputRef={searchInputRef} />

      </div>



      {errorMessage ? (

        <p className="app-launcher-panel__error" role="alert">

          {errorMessage}

        </p>

      ) : null}



      <div className="app-launcher-panel__scroll" id="launcher-app-results">

        {emptySearch ? (

          <p className="app-launcher-panel__empty">

            Aucun espace ne correspond à « {query} ».

          </p>

        ) : null}



        {showContinue && (continueItem || fallbackContinue) ? (

          <section className="app-launcher-section" aria-labelledby="launcher-continue-heading">

            <h3 id="launcher-continue-heading" className="app-launcher-section__title">

              Continuer

            </h3>

            <LauncherContinueCard

              item={(continueItem ?? fallbackContinue)!}

              onSelect={onSelect}

              isFallback={!continueItem && Boolean(fallbackContinue)}

            />

          </section>

        ) : null}



        {!emptySearch && availableItems.length > 0 ? (

          <section className="app-launcher-section" aria-labelledby="launcher-available-heading">

            <h3 id="launcher-available-heading" className="app-launcher-section__title">

              Espaces métier

            </h3>

            <LauncherProductGrid

              items={availableItems}

              onSelect={onSelect}

              onUnavailableClick={onUnavailableClick}

              labelledBy="launcher-available-heading"

              onNavigateAway={onNavigateAway}

            />

          </section>

        ) : null}



        {!emptySearch && soonItems.length > 0 ? (

          <section className="app-launcher-section" aria-labelledby="launcher-soon-heading">

            <h3 id="launcher-soon-heading" className="app-launcher-section__title">

              Bientôt disponibles

            </h3>

            <LauncherProductGrid

              items={soonItems}

              onUnavailableClick={onUnavailableClick}

              variant="coming_soon"

              labelledBy="launcher-soon-heading"

              onNavigateAway={onNavigateAway}

            />

          </section>

        ) : null}



        {!filtering && availableItems.length === 0 && soonItems.length === 0 ? (

          <p className="app-launcher-panel__empty">Aucun espace à afficher pour le moment.</p>

        ) : null}

      </div>



      <LauncherFooter onNavigateAway={onNavigateAway} />

    </div>

  )

}


