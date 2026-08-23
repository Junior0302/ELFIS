import { Link } from 'react-router-dom'
import { CoreProductVisual } from '../components/CoreProductVisual'
import { LANDING_HERO } from '../landing.copy'

type HeroSectionProps = {
  isAuthenticated: boolean
}

export function HeroSection({ isAuthenticated }: HeroSectionProps) {
  return (
    <section className="landing-hero" aria-labelledby="landing-hero-title">
      <div className="landing-hero__copy">
        <p className="landing-hero__eyebrow">{LANDING_HERO.eyebrow}</p>
        <h1 id="landing-hero-title">{LANDING_HERO.title}</h1>
        <p className="landing-hero__lead">{LANDING_HERO.lead}</p>
        <p className="landing-hero__lead landing-hero__lead--secondary">{LANDING_HERO.leadSecondary}</p>
        <p className="landing-hero__tagline">{LANDING_HERO.tagline}</p>
        <div className="landing-hero__actions">
          <a className="btn landing-hero__cta" href={LANDING_HERO.discoverHref}>
            {LANDING_HERO.discover}
          </a>
          {isAuthenticated ? (
            <Link className="btn secondary" to={LANDING_HERO.openWorkspaceTo}>
              {LANDING_HERO.openWorkspace}
            </Link>
          ) : (
            <>
              <Link className="btn secondary" to={LANDING_HERO.startTo}>
                {LANDING_HERO.start}
              </Link>
              <Link className="landing-hero__login" to={LANDING_HERO.loginTo}>
                {LANDING_HERO.login}
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="landing-hero__visual">
        <CoreProductVisual />
      </div>
    </section>
  )
}
