import { FeatureCard } from '../components/FeatureCard'
import { LandingIcon } from '../components/LandingIcon'

const FEATURES = [
  {
    icon: <LandingIcon name="grid" />,
    title: 'App Launcher',
    description: 'Passez d’un Pilot à l’autre depuis un composant plateforme unique.',
  },
  {
    icon: <LandingIcon name="link" />,
    title: 'Connexion des métiers',
    description: 'Sales, finance et documents reliés dans le même écosystème.',
  },
  {
    icon: <LandingIcon name="database" />,
    title: 'Données partagées',
    description: 'Une organisation, des droits clairs, moins de double saisie.',
  },
  {
    icon: <LandingIcon name="shield" />,
    title: 'Sécurité native',
    description: 'Chrome plateforme, sessions et contexte org maîtrisés.',
  },
  {
    icon: <LandingIcon name="building" />,
    title: 'Multi-workspaces',
    description: 'Pilotez plusieurs organisations sans perdre le fil.',
  },
  {
    icon: <LandingIcon name="spark" />,
    title: 'Expérience premium',
    description: 'Design System ELFIS, motion léger, interfaces respirantes.',
  },
] as const

export function FeaturesSection() {
  return (
    <section id="ressources" className="landing-section landing-features" aria-labelledby="landing-features-title">
      <div className="landing-section__intro">
        <p className="landing-kicker">Fonctionnalités</p>
        <h2 id="landing-features-title">Tout ce qu’il faut pour piloter</h2>
      </div>
      <div className="landing-features__grid">
        {FEATURES.map((f) => (
          <FeatureCard key={f.title} icon={f.icon} title={f.title} description={f.description} />
        ))}
      </div>
    </section>
  )
}
