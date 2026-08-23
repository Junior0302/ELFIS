import type { CSSProperties } from 'react'
import { WorkspaceSpaceIcon } from '../../workspaces/WorkspaceSpaceIcon'
import '../../workspaces/workspace-space-icon.css'
import { LANDING_VISUAL } from '../landing.copy'
import { PUBLIC_OPEN_SPACES } from '../landing.model'

/**
 * Visualisation produit — ELFIS Core au centre, trois Espaces ouverts.
 * Données d’interface génériques, sans KPI commerciaux.
 */
export function CoreProductVisual() {
  return (
    <div className="landing-visual-stage">
      <div className="landing-visual-stage__glow" aria-hidden />
      <div className="landing-visual-stage__ring" aria-hidden />
      <div className="landing-visual" role="img" aria-label={LANDING_VISUAL.ariaLabel}>
        <div className="landing-visual__chrome">
          <span className="landing-visual__dots" aria-hidden>
            <i />
            <i />
            <i />
          </span>
          <span className="landing-visual__chrome-title">{LANDING_VISUAL.chrome}</span>
          <span className="landing-visual__chrome-meta">{LANDING_VISUAL.chromeMeta}</span>
        </div>

        <div className="landing-visual__core">
          <p className="landing-visual__core-kicker">{LANDING_VISUAL.coreKicker}</p>
          <p className="landing-visual__core-title">{LANDING_VISUAL.coreTitle}</p>
          <ul className="landing-visual__traits">
            {LANDING_VISUAL.coreTraits.map((trait) => (
              <li key={trait}>{trait}</li>
            ))}
          </ul>
        </div>

        <div className="landing-visual__connectors" aria-hidden>
          <span className="landing-visual__stem" />
          <span className="landing-visual__rail" />
        </div>

        <div className="landing-visual__spaces">
          {PUBLIC_OPEN_SPACES.map((space) => (
            <article
              key={space.id}
              className={`landing-visual__space landing-visual__space--${space.id}`}
              style={
                {
                  '--space-accent': space.accent,
                  '--space-soft': space.accentSoft,
                } as CSSProperties
              }
            >
              <div className="landing-visual__space-head">
                <WorkspaceSpaceIcon
                  icon={space.icon}
                  accent={space.accent}
                  soft={space.accentSoft}
                  size="sm"
                />
                <div>
                  <h3>{space.label}</h3>
                  <p>{space.description}</p>
                </div>
              </div>
              <ul className="landing-visual__modules">
                {space.modules.map((moduleName) => (
                  <li key={moduleName}>
                    <span className="landing-visual__dot" />
                    {moduleName}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
