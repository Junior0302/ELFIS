import { useState } from 'react'
import { Link } from 'react-router-dom'
import heroImage from '../assets/comptapilot-home-hero.webp'
import { useAuth } from '../auth'

const benefits = [
  {
    number: '01',
    title: 'Comprendre vos chiffres',
    text: 'CA, marge, factures et alertes sont regroupés dans une vue claire pour le dirigeant.',
  },
  {
    number: '02',
    title: 'Gagner du temps',
    text: 'Déposez vos documents : l’OCR extrait les informations et prépare les écritures.',
  },
  {
    number: '03',
    title: 'Décider avec l’IA',
    text: 'Échangez naturellement avec Finance Agent pour obtenir une explication exploitable.',
  },
]

export default function HomePage() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="home-page">
      <header className="home-header">
        <Link className="home-brand" to="/" onClick={() => setMenuOpen(false)}>
          <img src="/favicon.svg" alt="" />
          <span>
            <strong>ComptaPilot IA</strong>
            <small>ELFIS Core</small>
          </span>
        </Link>

        <button
          className="home-menu-button"
          type="button"
          aria-label="Ouvrir le menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={`home-nav ${menuOpen ? 'open' : ''}`} aria-label="Navigation principale">
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
            <span className="home-eyebrow">Le copilote financier des dirigeants</span>
            <h1>Vos chiffres deviennent enfin simples à piloter.</h1>
            <p>
              Centralisez votre comptabilité et votre facturation. Posez ensuite vos questions à une
              IA qui vous répond clairement, avec les données réelles de votre entreprise.
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
              <span>Firebase sécurisé</span>
              <span>Données réelles</span>
              <span>Conçu en France</span>
            </div>
          </div>
          <div className="home-hero-visual">
            <img src={heroImage} alt="Un dirigeant pilote son entreprise avec ComptaPilot IA" />
            <div className="home-floating-card">
              <span className="home-status-dot" />
              <div>
                <strong>Finance Agent</strong>
                <small>Prêt à vous répondre</small>
              </div>
            </div>
          </div>
        </section>

        <section className="home-benefits" id="fonctionnalites">
          <div className="home-section-heading">
            <span>Une plateforme utile au quotidien</span>
            <h2>Moins de complexité. Plus de visibilité.</h2>
          </div>
          <div className="home-benefit-grid">
            {benefits.map((benefit) => (
              <article key={benefit.number} className="home-benefit-card">
                <span>{benefit.number}</span>
                <h3>{benefit.title}</h3>
                <p>{benefit.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="home-pricing" id="tarif">
          <div className="home-section-heading">
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
            <ul className="pricing-features">
              <li>Copilote financier IA</li>
              <li>OCR, comptabilité et exports</li>
              <li>Facturation et suivi d’activité</li>
              <li>Utilisateurs et organisation</li>
            </ul>
            <Link className="btn home-primary-cta" to={user ? '/abonnement' : '/register'}>
              {user ? 'Gérer mon abonnement' : 'Essayer gratuitement pendant 14 jours'}
            </Link>
          </article>
        </section>

        <section className="home-copilot-section" id="copilote">
          <div>
            <span className="home-eyebrow">Une conversation, pas un rapport compliqué</span>
            <h2>Demandez. Comprenez. Décidez.</h2>
            <p>
              « Pourquoi ma marge baisse ? », « Résume mon activité » ou simplement « Bonjour » :
              Finance Agent vous répond comme un interlocuteur, pas comme un tableau Excel.
            </p>
          </div>
          <div className="home-chat-demo" aria-label="Exemple de conversation">
            <div className="home-demo-message user">Bonjour, peux-tu résumer mon activité ?</div>
            <div className="home-demo-message assistant">
              Bien sûr. Je vais reprendre vos factures et vos indicateurs, puis vous expliquer les
              trois points importants en langage simple.
            </div>
          </div>
        </section>
      </main>

      <footer className="home-footer">
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
