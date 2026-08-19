const PILLARS = [
  {
    title: 'Une plateforme',
    text: 'ELFIS Core relie vos expertises dans un socle unique — identité, sécurité, organisation.',
  },
  {
    title: 'Plusieurs Pilot',
    text: 'Chaque métier dispose de son application : Compta, Sales, Docs, RH, Support…',
  },
  {
    title: 'Une seule connexion',
    text: 'Authentifiez-vous une fois. Passez d’un Pilot à l’autre sans rupture.',
  },
  {
    title: 'Une seule organisation',
    text: 'Workspaces, rôles et membres partagés à l’échelle de l’entreprise.',
  },
  {
    title: 'Une seule donnée',
    text: 'Les informations circulent entre Pilot selon vos droits — sans silos inutiles.',
  },
] as const

export function ApplicationsSection() {
  return (
    <section id="plateforme" className="landing-section landing-apps" aria-labelledby="landing-apps-title">
      <div className="landing-section__intro">
        <p className="landing-kicker">Plateforme</p>
        <h2 id="landing-apps-title">Une plateforme. Plusieurs Pilot.</h2>
        <p className="landing-section__lead">
          L’App Launcher ELFIS ouvre la famille d’applications — même Mark, même organisation,
          expertises distinctes.
        </p>
      </div>
      <ul className="landing-apps__grid">
        {PILLARS.map((item) => (
          <li key={item.title} className="landing-apps__card">
            <h3>{item.title}</h3>
            <p>{item.text}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
