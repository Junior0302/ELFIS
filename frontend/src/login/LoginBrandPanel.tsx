import { LoginBenefit } from './LoginBenefit'
import { LoginIllustration } from './LoginIllustration'

const BENEFITS = [
  {
    title: 'Une identité unique',
    text: 'Un compte pour toute la plateforme ELFIS Core.',
  },
  {
    title: 'Vos applications réunies',
    text: 'ComptaPilot, SalesPilot et les prochains Pilot.',
  },
  {
    title: 'Vos données protégées',
    text: 'Organisation, droits et continuité sécurisées.',
  },
] as const

export function LoginBrandPanel() {
  return (
    <aside className="elfis-login__brand-panel" aria-labelledby="elfis-login-hero-title">
      <p className="elfis-login__kicker">Espace sécurisé</p>
      <h2 id="elfis-login-hero-title" className="elfis-login__hero-title">
        Une connexion.
        <br />
        Tout votre écosystème.
      </h2>
      <p className="elfis-login__hero-lead">
        Accédez à ComptaPilot, SalesPilot et aux prochaines applications ELFIS depuis un espace
        unique et sécurisé.
      </p>
      <LoginIllustration />
      <ul className="elfis-login__benefits">
        {BENEFITS.map((b) => (
          <LoginBenefit key={b.title} title={b.title} text={b.text} />
        ))}
      </ul>
    </aside>
  )
}
