import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { GridItem, PlatformGrid } from '../unified-platform'
import { setLastProductId } from './lastProduct'
import { resolveSpaceSummaries } from './homeSignals'

type SpacesSectionProps = {
  lastProductId: string | null
  lastProductAt: string | null
}

/** Domaines métier OS — grille dense, accents Pilot uniquement sur indicateur. */
export function SpacesSection({ lastProductId, lastProductAt }: SpacesSectionProps) {
  const spaces = resolveSpaceSummaries(lastProductId, lastProductAt)

  return (
    <section className="cockpit-spaces" id="home-spaces" aria-labelledby="home-spaces-title" data-cockpit-spaces="v1">
      <div className="elfis-home__section-head elfis-home__section-head--compact">
        <h2 id="home-spaces-title">Vos espaces</h2>
        <p>Départements de l’entreprise — un seul OS.</p>
      </div>
      <PlatformGrid columns={12} gap={3} className="cockpit-spaces__grid">
        {spaces.map((space) => {
          const style = { '--space-accent': space.accent } as CSSProperties
          const body = (
            <>
              <span className="cockpit-space__accent" aria-hidden />
              <div className="cockpit-space__top">
                <strong className="cockpit-space__title">{space.title}</strong>
                <span className={`cockpit-space__status ${space.available ? 'is-on' : 'is-soon'}`}>
                  {space.statusLabel}
                </span>
              </div>
              <p className="cockpit-space__summary">{space.summary}</p>
              {space.poweredBy ? (
                <p className="cockpit-space__powered">{space.poweredBy}</p>
              ) : null}
            </>
          )

          if (!space.available || !space.to) {
            return (
              <GridItem key={space.id} span={6} spanMd={6} spanLg={3}>
                <div className="cockpit-space cockpit-space__tile is-disabled" style={style}>
                  {body}
                </div>
              </GridItem>
            )
          }

          return (
            <GridItem key={space.id} span={6} spanMd={6} spanLg={3}>
              <Link
                to={space.to}
                className="cockpit-space cockpit-space--link cockpit-space__tile"
                style={style}
                onClick={() => space.productId && setLastProductId(space.productId)}
              >
                {body}
              </Link>
            </GridItem>
          )
        })}
      </PlatformGrid>
    </section>
  )
}
