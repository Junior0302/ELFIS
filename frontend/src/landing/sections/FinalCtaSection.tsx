import { Link } from 'react-router-dom'
import { LANDING_FINAL_CTA, LANDING_HERO } from '../landing.copy'

type FinalCtaSectionProps = {
  isAuthenticated: boolean
}

export function FinalCtaSection({ isAuthenticated }: FinalCtaSectionProps) {
  return (
    <section className="landing-cta" aria-labelledby="landing-cta-title">
      <div className="landing-cta__panel">
        <div className="landing-cta__glow" aria-hidden />
        <h2 id="landing-cta-title">{LANDING_FINAL_CTA.title}</h2>
        <p>{LANDING_FINAL_CTA.lead}</p>
        <p className="landing-cta__tagline">{LANDING_FINAL_CTA.tagline}</p>
        <div className="landing-cta__actions">
          <a className="btn" href={LANDING_HERO.discoverHref}>
            {LANDING_FINAL_CTA.discover}
          </a>
          {isAuthenticated ? (
            <Link className="btn secondary landing-cta__ghost" to={LANDING_HERO.openWorkspaceTo}>
              {LANDING_HERO.openWorkspace}
            </Link>
          ) : (
            <>
              <Link className="btn secondary landing-cta__ghost" to={LANDING_HERO.startTo}>
                {LANDING_FINAL_CTA.start}
              </Link>
              <Link className="landing-cta__text" to={LANDING_HERO.loginTo}>
                {LANDING_FINAL_CTA.login}
              </Link>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
