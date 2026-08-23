import { LoginBenefit } from './LoginBenefit'

const BENEFITS = [
  {
    title: 'Accès sécurisé',
    text: 'Connexion chiffrée et protégée.',
    icon: 'shield',
    tone: 'secure' as const,
  },
  {
    title: 'Écosystème unifié',
    text: 'Toutes vos applications réunies.',
    icon: 'apps',
    tone: 'ecosystem' as const,
  },
  {
    title: 'Accès unique',
    text: 'Un accès rapide à vos espaces ELFIS.',
    icon: 'activity',
    tone: 'access' as const,
  },
] as const

export function LoginBrandPanel() {
  return (
    <aside className="elfis-login__brand-panel" aria-labelledby="elfis-login-hero-title">
      <h2 id="elfis-login-hero-title" className="elfis-login__hero-title">
        Bienvenue sur <span>ELFIS Core</span>
      </h2>
      <p className="elfis-login__hero-lead">
        Tout votre écosystème. Une seule connexion.
      </p>
      <ul className="elfis-login__benefits">
        {BENEFITS.map((b) => (
          <LoginBenefit key={b.title} title={b.title} text={b.text} icon={b.icon} tone={b.tone} />
        ))}
      </ul>
    </aside>
  )
}
