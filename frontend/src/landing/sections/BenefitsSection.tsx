const BENEFITS = [
  {
    title: 'Continuité cross-Pilot',
    text: 'Topbar plateforme, org et profil persistent quand vous changez d’application.',
  },
  {
    title: 'Identité maîtrisée',
    text: 'ELFIS Core porte le chrome ; chaque Pilot apporte sa couleur et son expertise.',
  },
  {
    title: 'Recherche & alertes unifiées',
    text: 'Retrouvez entités et notifications à l’échelle de la plateforme.',
  },
  {
    title: 'Prêt pour grandir',
    text: 'Ajoutez DocPilot, HRPilot ou SupportPilot sans changer de socle.',
  },
] as const

export function BenefitsSection() {
  return (
    <section className="landing-section landing-benefits" aria-labelledby="landing-benefits-title">
      <div className="landing-section__intro">
        <p className="landing-kicker">Pourquoi ELFIS</p>
        <h2 id="landing-benefits-title">Conçu pour connecter l’entreprise</h2>
      </div>
      <ul className="landing-benefits__grid">
        {BENEFITS.map((b) => (
          <li key={b.title}>
            <h3>{b.title}</h3>
            <p>{b.text}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
