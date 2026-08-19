import { Link } from 'react-router-dom'
import { HeroPilotCard } from '../components/HeroPilotCard'
import type { PilotCardId } from '../components/HeroPilotCard'

const PILOTS: Array<{ id: PilotCardId; name: string; blurb: string; orbit: string }> = [
  { id: 'salespilot', name: 'SalesPilot', blurb: 'Pipeline & relation', orbit: 'orbit-1' },
  { id: 'comptapilot', name: 'ComptaPilot', blurb: 'Finance fiable', orbit: 'orbit-2' },
  { id: 'docpilot', name: 'DocPilot', blurb: 'Flux documentaires', orbit: 'orbit-3' },
  { id: 'analyticspilot', name: 'AnalyticsPilot', blurb: 'Pilotage data', orbit: 'orbit-4' },
  { id: 'supportpilot', name: 'SupportPilot', blurb: 'Service client', orbit: 'orbit-5' },
  { id: 'hrpilot', name: 'HRPilot', blurb: 'Équipes & RH', orbit: 'orbit-6' },
]

type HeroSectionProps = {
  primaryTo: string
  secondaryTo: string
  isAuthenticated: boolean
}

export function HeroSection({ primaryTo, secondaryTo, isAuthenticated }: HeroSectionProps) {
  return (
    <section className="landing-hero" aria-labelledby="landing-hero-title">
      <div className="landing-hero__copy">
        <p className="landing-hero__eyebrow">ELFIS Core</p>
        <h1 id="landing-hero-title">Une plateforme. Plusieurs expertises.</h1>
        <p className="landing-hero__lead">
          Connectez finance, ventes, documents et métiers autour d&apos;une seule organisation —
          une connexion, des données partagées, des Pilot spécialisés.
        </p>
        <div className="landing-hero__actions">
          <Link className="btn landing-hero__cta" to={primaryTo}>
            {isAuthenticated ? 'Accéder à mon espace' : 'Découvrir ELFIS'}
          </Link>
          <Link className="btn secondary" to={secondaryTo}>
            {isAuthenticated ? 'Tableau de bord' : 'Se connecter'}
          </Link>
        </div>
      </div>

      <div className="landing-hero__visual" aria-hidden="false">
        <div className="landing-hero__orbit" role="img" aria-label="Écosystème des applications Pilot">
          <div className="landing-hero__core">
            <img src="/favicon.svg" alt="" width={72} height={72} decoding="async" />
            <span>ELFIS</span>
          </div>
          <span className="landing-hero__ring landing-hero__ring--a" />
          <span className="landing-hero__ring landing-hero__ring--b" />
          <span className="landing-hero__flow landing-hero__flow--1" />
          <span className="landing-hero__flow landing-hero__flow--2" />
          <span className="landing-hero__flow landing-hero__flow--3" />
          {PILOTS.map((pilot) => (
            <div key={pilot.id} className={`landing-hero__card-slot landing-hero__card-slot--${pilot.orbit}`}>
              <HeroPilotCard id={pilot.id} name={pilot.name} blurb={pilot.blurb} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
