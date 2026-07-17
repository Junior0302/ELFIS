import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import heroImage from '../assets/comptapilot-home-hero.webp'
import { useAuth } from '../auth'
import HomeCursor from '../components/HomeCursor'
import TypeRotate from '../components/TypeRotate'

const HomeParticles = lazy(() => import('../components/HomeParticles'))

function IconChart({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 19V5M4 19h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path
        d="M8 15v-3M12 15V8M16 15v-5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

function IconScan({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 4H5a1 1 0 0 0-1 1v2M17 4h2a1 1 0 0 1 1 1v2M7 20H5a1 1 0 0 1-1-1v-2M17 20h2a1 1 0 0 0 1-1v-2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path d="M8 12h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="7" y="8" width="10" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function IconSpark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function IconShield({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3.5 5.5 6v5.2c0 4.1 2.7 7.8 6.5 9.3 3.8-1.5 6.5-5.2 6.5-9.3V6L12 3.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="m9.2 12 1.8 1.8 3.8-3.8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconDatabase({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <ellipse cx="12" cy="6" rx="6.5" ry="2.4" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M5.5 6v6c0 1.3 2.9 2.4 6.5 2.4s6.5-1.1 6.5-2.4V6"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path
        d="M5.5 12v6c0 1.3 2.9 2.4 6.5 2.4s6.5-1.1 6.5-2.4v-6"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  )
}

function IconFrance({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="8.2" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 3.8v16.4M3.8 12h16.4M6.2 6.2c2.4 2.1 4.1 5.1 4.1 8.8 0 1.4-.3 2.7-.8 3.9M17.8 6.2c-2.4 2.1-4.1 5.1-4.1 8.8 0 1.4.3 2.7.8 3.9"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  )
}

function IconInvoice({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 3.5h10a1.5 1.5 0 0 1 1.5 1.5v14.2l-2.1-1.2-2.1 1.2-2.1-1.2-2.1 1.2-2.1-1.2-2.1 1.2V5A1.5 1.5 0 0 1 7 3.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M9 8h6M9 11.5h6M9 15h3.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

function IconUsers({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="9" cy="8" r="3" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M3.8 18.2c.7-2.4 2.7-3.7 5.2-3.7s4.5 1.3 5.2 3.7"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="16.5" cy="9" r="2.3" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M15.2 14.6c1.9.2 3.4 1.2 4 2.9"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

const benefits = [
  {
    icon: <IconChart />,
    title: 'Comprendre vos chiffres',
    text: 'CA, marge, factures et alertes regroupés dans une vue claire pour le dirigeant.',
  },
  {
    icon: <IconScan />,
    title: 'Gagner du temps',
    text: 'Déposez vos documents : l’OCR extrait les informations et prépare les écritures.',
  },
  {
    icon: <IconSpark />,
    title: 'Décider avec l’IA',
    text: 'Échangez avec Finance Agent pour obtenir une explication exploitable, en langage simple.',
  },
]

const pricingFeatures: { icon: ReactNode; label: string }[] = [
  { icon: <IconSpark />, label: 'Copilote financier IA' },
  { icon: <IconScan />, label: 'OCR, comptabilité et exports' },
  { icon: <IconInvoice />, label: 'Facturation et suivi d’activité' },
  { icon: <IconUsers />, label: 'Utilisateurs et organisation' },
]

export default function HomePage() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const pageRef = useRef<HTMLDivElement>(null)
  const navRef = useRef<HTMLElement>(null)
  const menuReady = useRef(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const root = pageRef.current
    if (!root) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    root.classList.add('is-booting')
    let cancelled = false
    let revert: (() => void) | undefined

    void (async () => {
      const [{ default: gsap }, { ScrollTrigger }] = await Promise.all([
        import('gsap'),
        import('gsap/ScrollTrigger'),
      ])
      if (cancelled || !pageRef.current) return
      gsap.registerPlugin(ScrollTrigger)

      const ctx = gsap.context(() => {
        if (reduce) {
          gsap.set(
            '.home-header, .home-brand-hero, .home-type-line, .home-hero-copy > h1, .home-hero-lead, .home-hero-actions .btn, .home-trust span, .home-hero-visual, .home-agent-strip',
            { clearProps: 'all', opacity: 1, y: 0, x: 0 },
          )
          root.classList.remove('is-booting')
          return
        }

        const intro = gsap.timeline({
          defaults: { ease: 'power3.out' },
          onStart: () => root.classList.remove('is-booting'),
        })
        intro
          .from('.home-header', { y: -28, opacity: 0, duration: 0.7 })
          .from(
            '.home-nav > a, .home-nav .btn',
            { y: -12, opacity: 0, duration: 0.45, stagger: 0.06 },
            '-=0.35',
          )
          .from('.home-brand-hero', { y: 36, opacity: 0, duration: 0.75 }, '-=0.25')
          .from('.home-type-line', { y: 28, opacity: 0, duration: 0.65 }, '-=0.45')
          .from('.home-hero-copy > h1', { y: 24, opacity: 0, duration: 0.6 }, '-=0.4')
          .from('.home-hero-lead', { y: 18, opacity: 0, duration: 0.55 }, '-=0.35')
          .from(
            '.home-hero-actions .btn',
            { y: 16, opacity: 0, duration: 0.5, stagger: 0.08 },
            '-=0.3',
          )
          .from('.home-trust span', { y: 12, opacity: 0, duration: 0.4, stagger: 0.07 }, '-=0.25')
          .from('.home-hero-visual', { x: 40, opacity: 0, duration: 0.85 }, '-=0.85')
          .from('.home-agent-strip', { y: 20, opacity: 0, duration: 0.5 }, '-=0.35')

        gsap.to('.home-hero-frame', {
          y: -10,
          duration: 3.6,
          ease: 'sine.inOut',
          yoyo: true,
          repeat: -1,
        })

        gsap.utils.toArray<HTMLElement>('.home-reveal').forEach((el) => {
          gsap.from(el, {
            scrollTrigger: {
              trigger: el,
              start: 'top 85%',
              toggleActions: 'play none none none',
            },
            y: 48,
            opacity: 0,
            duration: 0.85,
            ease: 'power3.out',
          })
        })

        gsap.from('.home-benefit-card', {
          scrollTrigger: {
            trigger: '.home-benefit-grid',
            start: 'top 80%',
          },
          y: 56,
          opacity: 0,
          duration: 0.75,
          stagger: 0.12,
          ease: 'power3.out',
        })

        gsap.from('.home-pricing-card', {
          scrollTrigger: {
            trigger: '.home-pricing-card',
            start: 'top 82%',
          },
          y: 40,
          scale: 0.97,
          opacity: 0,
          duration: 0.8,
          ease: 'power3.out',
        })

        gsap.from('.home-demo-message', {
          scrollTrigger: {
            trigger: '.home-chat-demo',
            start: 'top 80%',
          },
          y: 18,
          opacity: 0,
          duration: 0.55,
          stagger: 0.18,
          ease: 'power2.out',
        })
      }, root)

      revert = () => ctx.revert()
    })()

    return () => {
      cancelled = true
      revert?.()
    }
  }, [])

  useEffect(() => {
    const nav = navRef.current
    if (!nav || window.innerWidth > 1024) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (!menuReady.current) {
      menuReady.current = true
      return
    }

    let cancelled = false

    void (async () => {
      if (reduce) {
        if (menuOpen) nav.classList.add('open')
        else nav.classList.remove('open')
        return
      }

      const { default: gsap } = await import('gsap')
      if (cancelled) return

      if (menuOpen) {
        nav.classList.add('open')
        gsap.fromTo(
          nav,
          { autoAlpha: 0, y: -12, scale: 0.98 },
          { autoAlpha: 1, y: 0, scale: 1, duration: 0.35, ease: 'power2.out' },
        )
        gsap.fromTo(
          nav.querySelectorAll('a, .btn'),
          { y: 10, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.3, stagger: 0.05, delay: 0.05, ease: 'power2.out' },
        )
      } else {
        gsap.to(nav, {
          autoAlpha: 0,
          y: -8,
          duration: 0.22,
          ease: 'power2.in',
          onComplete: () => nav.classList.remove('open'),
        })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [menuOpen])

  return (
    <div className="home-page" ref={pageRef}>
      <HomeCursor />
      <Suspense fallback={null}>
        <HomeParticles />
      </Suspense>
      <div className="home-atmosphere" aria-hidden="true">
        <span className="home-orb home-orb-a" />
        <span className="home-orb home-orb-b" />
        <span className="home-orb home-orb-c" />
      </div>

      <header className={`home-header ${scrolled ? 'is-scrolled' : ''}`}>
        <Link className="home-brand" to="/" onClick={() => setMenuOpen(false)}>
          <img src="/favicon.svg" alt="" />
          <span>
            <strong>ComptaPilot IA</strong>
            <small>ELFIS Core</small>
          </span>
        </Link>

        <button
          className={`home-menu-button ${menuOpen ? 'is-open' : ''}`}
          type="button"
          aria-label="Ouvrir le menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav
          ref={navRef}
          className={`home-nav ${menuOpen ? 'open' : ''}`}
          aria-label="Navigation principale"
        >
          <a href="#fonctionnalites" onClick={() => setMenuOpen(false)}>
            Fonctionnalités
          </a>
          <a href="#copilote" onClick={() => setMenuOpen(false)}>
            Copilote IA
          </a>
          <a href="#tarif" onClick={() => setMenuOpen(false)}>
            Tarif
          </a>
          {user ? (
            <Link className="btn" to="/dashboard">
              Ouvrir mon espace
            </Link>
          ) : (
            <>
              <Link className="home-login-link" to="/login">
                Connexion
              </Link>
              <Link className="btn" to="/register">
                Créer un compte
              </Link>
            </>
          )}
        </nav>
      </header>

      <main>
        <section className="home-hero">
          <div className="home-hero-copy">
            <p className="home-brand-hero">ComptaPilot IA</p>
            <p className="home-type-line">
              Facilite <TypeRotate />
            </p>
            <h1>Vos chiffres deviennent enfin simples à piloter.</h1>
            <p className="home-hero-lead">
              Centralisez comptabilité et facturation. Posez vos questions à une IA qui répond
              clairement, avec les données réelles de votre entreprise.
            </p>
            <div className="home-hero-actions">
              <Link className="btn home-primary-cta" to={user ? '/dashboard' : '/register'}>
                {user ? 'Accéder au tableau de bord' : 'Commencer gratuitement'}
              </Link>
              <Link className="btn secondary" to={user ? '/copilote' : '/login'}>
                {user ? 'Parler au copilote' : 'J’ai déjà un compte'}
              </Link>
            </div>
            <div className="home-trust">
              <span>
                <IconShield className="home-trust-icon" />
                Connexion sécurisée
              </span>
              <span>
                <IconDatabase className="home-trust-icon" />
                Données réelles
              </span>
              <span>
                <IconFrance className="home-trust-icon" />
                Conçu en France
              </span>
            </div>
          </div>

          <div className="home-hero-visual">
            <div className="home-hero-frame">
              <img src={heroImage} alt="Un dirigeant pilote son entreprise avec ComptaPilot IA" />
              <div className="home-hero-glow" aria-hidden="true" />
            </div>
            <aside className="home-agent-strip" aria-label="Statut Finance Agent">
              <span className="home-status-dot" />
              <div>
                <strong>Finance Agent</strong>
                <small>Prêt à vous répondre</small>
              </div>
            </aside>
          </div>
        </section>

        <section className="home-benefits" id="fonctionnalites">
          <div className="home-section-heading home-reveal">
            <span>Une plateforme utile au quotidien</span>
            <h2>Moins de complexité. Plus de visibilité.</h2>
          </div>
          <div className="home-benefit-grid">
            {benefits.map((benefit) => (
              <article key={benefit.title} className="home-benefit-card">
                <div className="home-benefit-icon">{benefit.icon}</div>
                <h3>{benefit.title}</h3>
                <p>{benefit.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="home-pricing" id="tarif">
          <div className="home-section-heading home-reveal">
            <span>Un tarif simple</span>
            <h2>Tout ComptaPilot, sans surprise.</h2>
          </div>
          <article className="home-pricing-card">
            <div>
              <span className="home-eyebrow">ComptaPilot Pro</span>
              <div className="home-price">
                <strong>19 €</strong>
                <span>/ mois</span>
              </div>
              <p>14 jours d’essai. Carte demandée au départ, résiliation depuis votre espace.</p>
            </div>
            <ul className="pricing-features home-pricing-features">
              {pricingFeatures.map((item) => (
                <li key={item.label}>
                  <span className="home-feature-icon">{item.icon}</span>
                  {item.label}
                </li>
              ))}
            </ul>
            <Link className="btn home-primary-cta" to={user ? '/abonnement' : '/register'}>
              {user ? 'Gérer mon abonnement' : 'Essayer gratuitement pendant 14 jours'}
            </Link>
          </article>
        </section>

        <section className="home-copilot-section" id="copilote">
          <div className="home-reveal">
            <span className="home-eyebrow">Une conversation, pas un rapport compliqué</span>
            <h2>Demandez. Comprenez. Décidez.</h2>
            <p>
              « Pourquoi ma marge baisse ? », « Résume mon activité » ou simplement « Bonjour » :
              Finance Agent vous répond comme un interlocuteur, pas comme un tableau Excel.
            </p>
          </div>
          <div className="home-chat-demo home-reveal" aria-label="Exemple de conversation">
            <div className="home-chat-header">
              <span className="home-status-dot" />
              <strong>Finance Agent</strong>
            </div>
            <div className="home-demo-message user">Bonjour, peux-tu résumer mon activité ?</div>
            <div className="home-demo-message assistant">
              Bien sûr. Je vais reprendre vos factures et vos indicateurs, puis vous expliquer les
              trois points importants en langage simple.
            </div>
            <div className="home-typing" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </div>
        </section>
      </main>

      <footer className="home-footer home-reveal">
        <div className="home-brand">
          <img src="/favicon.svg" alt="" />
          <span>
            <strong>ComptaPilot IA</strong>
            <small>Propulsé par ELFIS Core</small>
          </span>
        </div>
        <div>
          <Link to="/login">Connexion</Link>
          <Link to="/register">Créer un compte</Link>
        </div>
      </footer>
    </div>
  )
}
