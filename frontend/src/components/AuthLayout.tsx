import { useEffect, useRef } from 'react'
import { Link, Outlet } from 'react-router-dom'
import gsap from 'gsap'
import './auth.css'

const bullets = [
  {
    title: 'Connexion sécurisée',
    text: 'Email et mot de passe protégés de bout en bout.',
  },
  {
    title: 'Données réelles',
    text: 'Votre organisation, vos chiffres — pas de démo fictive.',
  },
  {
    title: 'Copilote financier',
    text: 'Comprenez, décidez et pilotez avec l’IA.',
  },
]

export default function AuthLayout() {
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const ctx = gsap.context(() => {
      gsap.from('.auth-aside-inner > *', {
        y: 22,
        opacity: 0,
        duration: 0.65,
        stagger: 0.08,
        ease: 'power3.out',
      })
      gsap.from('.auth-main .auth-card', {
        y: 28,
        opacity: 0,
        duration: 0.7,
        delay: 0.12,
        ease: 'power3.out',
      })
    }, root)

    return () => ctx.revert()
  }, [])

  return (
    <div className="auth-shell" ref={rootRef}>
      <aside className="auth-aside">
        <div className="auth-aside-glow" aria-hidden="true" />
        <div className="auth-aside-inner">
          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="" className="auth-logo" width={48} height={48} />
            <span>
              <strong>ComptaPilot IA</strong>
              <small>ELFIS Core</small>
            </span>
          </Link>
          <p className="auth-kicker">Espace sécurisé</p>
          <h1 className="auth-title">Pilotez vos chiffres avec clarté.</h1>
          <p className="auth-lead">
            Comptabilité, facturation et décisions assistées par l’IA — pour les dirigeants qui
            veulent y voir clair.
          </p>
          <ul className="auth-bullets">
            {bullets.map((item) => (
              <li key={item.title}>
                <span className="auth-bullet-icon" aria-hidden="true" />
                <div>
                  <strong>{item.title}</strong>
                  <small>{item.text}</small>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <main className="auth-main">
        <Outlet />
      </main>
    </div>
  )
}
