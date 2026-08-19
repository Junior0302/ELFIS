import { Link } from 'react-router-dom'

type CTASectionProps = {
  primaryTo: string
  secondaryTo: string
  isAuthenticated: boolean
}

export function CTASection({ primaryTo, secondaryTo, isAuthenticated }: CTASectionProps) {
  return (
    <section id="tarifs" className="landing-cta" aria-labelledby="landing-cta-title">
      <div className="landing-cta__panel">
        <h2 id="landing-cta-title">Prêt à connecter votre entreprise ?</h2>
        <p>
          Rejoignez la plateforme ELFIS Core et ouvrez vos Pilot — une connexion, une organisation,
          des expertises reliées.
        </p>
        <div className="landing-cta__actions">
          <Link className="btn" to={primaryTo}>
            {isAuthenticated ? 'Ouvrir mon espace' : 'Découvrir ELFIS'}
          </Link>
          <Link className="btn secondary landing-cta__ghost" to={secondaryTo}>
            {isAuthenticated ? 'Tableau de bord' : 'Connexion'}
          </Link>
        </div>
      </div>
    </section>
  )
}
