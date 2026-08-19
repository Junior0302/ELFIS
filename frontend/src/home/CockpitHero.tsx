import { Link } from 'react-router-dom'
import { ElfisButtonLink } from '../unified-platform'
import { CockpitHeroVisual } from './CockpitHeroVisual'
import type { HomeSignal } from './homeSignals'

type CockpitHeroProps = {
  firstName: string
  orgName: string
  healthLabel: string
  healthOk: boolean
  signals: HomeSignal[]
}

export function CockpitHero({
  firstName,
  orgName,
  healthLabel,
  healthOk,
  signals,
}: CockpitHeroProps) {
  const primarySignal = signals.find((s) => s.tone === 'attention') ?? signals[0]
  const calm = signals.length === 0

  return (
    <section
      className="cockpit-hero home-hero cockpit-hero--os cockpit-hero--signature"
      aria-labelledby="home-welcome-title"
      data-cockpit-hero="v3"
    >
      <div className="cockpit-hero__atmosphere" aria-hidden />
      <div className="home-hero__copy">
        <p className="cockpit-hero__brand">ELFIS</p>
        <h1 id="home-welcome-title">Bonjour {firstName}</h1>
        <p className="home-hero__lede">
          {orgName && orgName !== '—' ? orgName : 'Organisation non sélectionnée'}
          <span className="cockpit-hero__sep" aria-hidden>
            ·
          </span>
          <span className={healthOk ? 'cockpit-hero__health is-ok' : 'cockpit-hero__health is-warn'}>
            {healthLabel}
          </span>
        </p>

        <div className="cockpit-hero__detect" aria-live="polite">
          <p className="cockpit-hero__detect-label">Aujourd’hui ELFIS a détecté</p>
          {calm ? (
            <p className="cockpit-hero__detect-empty">
              Rien d’urgent — la plateforme est calme.
            </p>
          ) : (
            <ul className="cockpit-hero__signals">
              {signals.slice(0, 3).map((s) => (
                <li key={s.id} data-tone={s.tone}>
                  {s.href ? <Link to={s.href}>{s.label}</Link> : s.label}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="cockpit-hero__cta">
          <ElfisButtonLink to="#home-continue" variant="primary">
            Commencer ma journée
          </ElfisButtonLink>
          {primarySignal?.href ? (
            <ElfisButtonLink to={primarySignal.href} variant="secondary" className="cockpit-hero__cta-secondary">
              Traiter l’essentiel
            </ElfisButtonLink>
          ) : (
            <ElfisButtonLink to="#home-intel" variant="secondary" className="cockpit-hero__cta-secondary">
              Voir les conseils
            </ElfisButtonLink>
          )}
        </div>
      </div>
      <CockpitHeroVisual className="cockpit-hero-visual--signature" />
    </section>
  )
}
