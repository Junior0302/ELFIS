import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { trackProductEvent } from '../productEvents'
import type { CommercialStatus } from '../subscription'
import {
  TRIAL_DISCOVERY_SLIDES,
  TRIAL_ONBOARDING_BENEFITS,
  TRIAL_ONBOARDING_STEPS,
  TRIAL_PREVIEW_SAMPLE,
  TRIAL_TRUST_ITEMS,
} from '../trialOnboarding'

type Props = {
  commercialStatus: CommercialStatus
  canManage: boolean
  orgName?: string
  firstName?: string
}

function fallbackCopy(status: CommercialStatus): {
  title: string
  lead: string
  primaryCta: string
} {
  switch (status) {
    case 'expired':
      return {
        title: 'Votre accès a expiré',
        lead: 'Renouvelez pour retrouver votre espace de pilotage.',
        primaryCta: 'Souscrire à nouveau',
      }
    case 'suspended':
      return {
        title: 'Accès temporairement suspendu',
        lead: 'Ouvrez l’abonnement ou contactez le support.',
        primaryCta: 'Voir mon abonnement',
      }
    case 'grace':
      return {
        title: 'Paiement à régulariser',
        lead: 'Régularisez pour conserver l’accès complet.',
        primaryCta: 'Régulariser mon paiement',
      }
    default:
      return {
        title: 'Accès requis',
        lead: 'Activez un essai ou un abonnement pour continuer.',
        primaryCta: 'Gérer mon abonnement',
      }
  }
}

function DashboardPreview() {
  const s = TRIAL_PREVIEW_SAMPLE
  return (
    <div className="fi-preview" aria-hidden="true">
      <div className="fi-preview-top">
        <span className="fi-preview-pill">Aperçu produit</span>
        <div className="fi-preview-health">
          <span>Health Score</span>
          <strong>
            {s.healthScore}
            <em>{s.healthGrade}</em>
          </strong>
        </div>
      </div>

      <div className="fi-preview-kpis">
        <div>
          <span>Trésorerie</span>
          <strong>{s.treasury}</strong>
        </div>
        <div>
          <span>Chiffre d’affaires</span>
          <strong>{s.revenue}</strong>
        </div>
        <div>
          <span>Impayés</span>
          <strong>{s.unpaid}</strong>
        </div>
      </div>

      <div className="fi-preview-mid">
        <div className="fi-preview-curve">
          <svg viewBox="0 0 200 72" preserveAspectRatio="none">
            <defs>
              <linearGradient id="fiCurveFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(167,230,198,0.45)" />
                <stop offset="100%" stopColor="rgba(167,230,198,0)" />
              </linearGradient>
            </defs>
            <path
              d="M0 52 C 25 50, 35 42, 50 38 S 75 48, 100 30 S 135 14, 160 24 S 185 34, 200 20 L200 72 L0 72 Z"
              fill="url(#fiCurveFill)"
            />
            <path
              d="M0 52 C 25 50, 35 42, 50 38 S 75 48, 100 30 S 135 14, 160 24 S 185 34, 200 20"
              fill="none"
              stroke="rgba(190,240,210,0.95)"
              strokeWidth="2.4"
              strokeLinecap="round"
            />
          </svg>
          <span>Courbe de trésorerie · exemple</span>
        </div>
        <div className="fi-preview-donut">
          <span>{s.healthScore}</span>
          <small>Santé</small>
        </div>
      </div>

      <div className="fi-preview-alert">⚠ {s.alert}</div>

      <div className="fi-preview-ai">
        <span className="fi-preview-bot">✦</span>
        <div>
          <strong>Copilote IA</strong>
          <p>« {s.copilote} »</p>
        </div>
      </div>

      <p className="fi-preview-caption">Ce que vous verrez une fois l’essai activé</p>
    </div>
  )
}

/**
 * Concept 6 — Landing page intégrée (promesse avant le dashboard).
 * Narration : Bienvenue → prêt → résultat → CTA. Le reste au scroll.
 */
export default function TrialActivationState({
  commercialStatus,
  canManage,
  orgName,
  firstName,
}: Props) {
  const titleId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const [tourOpen, setTourOpen] = useState(false)
  const [tourStep, setTourStep] = useState(0)

  const premium =
    commercialStatus === 'none' ||
    commercialStatus === 'trial_available' ||
    commercialStatus === 'checkout_pending'

  const greetName = (firstName || '').trim()
  const heroTitle = greetName ? `Bienvenue ${greetName} 👋` : 'Bienvenue 👋'

  useEffect(() => {
    if (!premium) return
    trackProductEvent('trial_onboarding_viewed', {
      status: commercialStatus,
      org: orgName || null,
    })
  }, [premium, commercialStatus, orgName])

  useEffect(() => {
    if (!premium || !rootRef.current) return
    const root = rootRef.current
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let revert: (() => void) | undefined
    let cancelled = false

    void (async () => {
      const { default: gsap } = await import('gsap')
      if (cancelled || !rootRef.current) return
      const ctx = gsap.context(() => {
        if (reduce) {
          gsap.set('.fi-reveal', { clearProps: 'all', opacity: 1, y: 0 })
          return
        }
        gsap.from('.fi-reveal', {
          y: 14,
          opacity: 0,
          duration: 0.48,
          stagger: 0.09,
          ease: 'power2.out',
        })
      }, root)
      revert = () => ctx.revert()
    })()

    return () => {
      cancelled = true
      revert?.()
    }
  }, [premium])

  if (!premium) {
    const copy = fallbackCopy(commercialStatus)
    return (
      <section className="panel dashboard-gate" aria-labelledby={titleId}>
        <h2 id={titleId}>{copy.title}</h2>
        <p className="muted">{copy.lead}</p>
        {canManage ? (
          <div className="dashboard-gate-actions">
            <Link className="btn" to="/abonnement">
              {copy.primaryCta}
            </Link>
          </div>
        ) : (
          <p className="muted">Demandez à un administrateur d’intervenir.</p>
        )}
      </section>
    )
  }

  const isCheckout = commercialStatus === 'checkout_pending'
  const primaryLabel = isCheckout
    ? 'Finaliser mon activation'
    : '🚀 Commencer gratuitement pendant 14 jours'
  const primaryTo = '/abonnement'
  const currentStepIndex = 0
  const progressPct = 20

  return (
    <div className="fi-page" ref={rootRef} aria-labelledby={titleId}>
      {/* ZONE 1 — Promesse (100 % viewport) */}
      <section className="fi-zone fi-zone-hero" aria-label="Bienvenue">
        <div className="fi-hero-story fi-reveal">
          <header className="fi-hero">
            <h1 id={titleId} className="fi-hero-title">
              {heroTitle}
            </h1>
            <p className="fi-hero-ready">Votre entreprise est prête.</p>
            <p className="fi-hero-lead">
              Dans moins de deux minutes, ComptaPilot commencera à analyser automatiquement votre
              activité et vous aidera à prendre de meilleures décisions.
            </p>
            <ul className="fi-checks" aria-label="Engagements">
              <li>
                <span aria-hidden>✓</span> 14 jours gratuits
              </li>
              <li>
                <span aria-hidden>✓</span> Sans engagement
              </li>
              <li>
                <span aria-hidden>✓</span> Configuration en moins de 2 minutes
              </li>
            </ul>
          </header>

          <div className="fi-cta">
            {canManage ? (
              <>
                <Link
                  className="btn fi-cta-primary"
                  to={primaryTo}
                  onClick={() =>
                    trackProductEvent('trial_cta_clicked', {
                      status: commercialStatus,
                      target: primaryTo,
                    })
                  }
                >
                  {primaryLabel}
                </Link>
                <ul className="fi-cta-meta">
                  <li>Aucune installation</li>
                  <li>Sans engagement</li>
                  <li>Annulation à tout moment</li>
                  <li>Aucun prélèvement aujourd’hui</li>
                </ul>
                <button
                  type="button"
                  className="fi-cta-secondary"
                  onClick={() => {
                    setTourOpen(true)
                    setTourStep(0)
                    trackProductEvent('feature_discovery_opened', { mode: 'tour' })
                  }}
                >
                  Découvrir en 30 secondes
                </button>
              </>
            ) : (
              <p className="muted">
                Demandez à un administrateur d’activer l’essai pour cette organisation.
              </p>
            )}
          </div>
        </div>

        <div className="fi-hero-visual fi-reveal" aria-label="Résultat attendu">
          <p className="fi-hero-visual-label">Voici le résultat que vous allez obtenir</p>
          <DashboardPreview />
        </div>
      </section>

      {/* ZONE 2 — Bénéfices */}
      <section className="fi-zone fi-zone-benefits fi-reveal" aria-labelledby="fi-benefits-title">
        <p className="fi-zone-kicker">Ce que ComptaPilot fait pour vous</p>
        <h2 id="fi-benefits-title">Voici ce que vous allez gagner</h2>
        <div className="fi-benefit-grid">
          {TRIAL_ONBOARDING_BENEFITS.map((b) => (
            <article key={b.id} className="fi-benefit">
              <span className="fi-benefit-icon" aria-hidden>
                {b.icon}
              </span>
              <h3>{b.title}</h3>
              <p>{b.text}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ZONE 3 — Configuration */}
      <section className="fi-zone fi-zone-config fi-reveal" aria-labelledby="fi-progress-title">
        <div className="fi-progress">
          <div className="fi-progress-head">
            <div>
              <p className="fi-zone-kicker">Prochaines étapes</p>
              <h2 id="fi-progress-title">Configuration</h2>
            </div>
            <span className="fi-progress-meta">
              {progressPct} % · Étape {currentStepIndex + 1} sur {TRIAL_ONBOARDING_STEPS.length}
            </span>
          </div>
          <div
            className="fi-progress-bar"
            role="progressbar"
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Progression de configuration"
          >
            <span style={{ width: `${progressPct}%` }} />
          </div>
          <ol className="fi-steps">
            {TRIAL_ONBOARDING_STEPS.map((step, index) => {
              const current = index === currentStepIndex
              const done = index < currentStepIndex
              return (
                <li
                  key={step.id}
                  className={done ? 'is-done' : current ? 'is-current' : 'is-locked'}
                  aria-current={current ? 'step' : undefined}
                >
                  <span className="fi-step-mark" aria-hidden>
                    {done ? '✓' : current ? '●' : '○'}
                  </span>
                  <span>
                    {step.label}
                    {!done && !current ? (
                      <span className="sr-only"> — après activation de l’essai</span>
                    ) : null}
                  </span>
                </li>
              )
            })}
          </ol>
        </div>
      </section>

      {/* ZONE 4 — Confiance puis témoignage */}
      <section className="fi-zone fi-zone-trust fi-reveal" aria-labelledby="fi-trust-title">
        <p className="fi-zone-kicker">Sécurité &amp; sérieux</p>
        <h2 id="fi-trust-title">Pourquoi faire confiance à ComptaPilot ?</h2>
        <ul className="fi-trust-list">
          {TRIAL_TRUST_ITEMS.map((item) => (
            <li key={item.id}>
              <span className="fi-trust-icon" aria-hidden>
                {item.icon}
              </span>
              <span>{item.label}</span>
            </li>
          ))}
        </ul>

        <figure className="fi-quote">
          <p className="fi-stars" aria-label="Note 5 sur 5">
            ★★★★★
          </p>
          <blockquote>
            <p>
              « En deux jours, j’ai compris ma trésorerie. Je ne reviens plus à mes tableurs. »
            </p>
          </blockquote>
          <figcaption className="fi-person">
            <span className="fi-avatar" aria-hidden>
              JD
            </span>
            <span>
              <strong>Julien Dupont</strong>
              <span className="fi-role">Entrepreneur · services</span>
            </span>
          </figcaption>
        </figure>
      </section>

      {tourOpen ? (
        <div
          className="fi-tour-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="fi-tour-title"
        >
          <div className="fi-tour-card">
            <button
              type="button"
              className="fi-tour-close"
              onClick={() => setTourOpen(false)}
              aria-label="Fermer"
            >
              ×
            </button>
            <p className="fi-tour-kicker">En 30 secondes</p>
            <h2 id="fi-tour-title">{TRIAL_DISCOVERY_SLIDES[tourStep].title}</h2>
            <p>{TRIAL_DISCOVERY_SLIDES[tourStep].text}</p>
            <div className="fi-tour-actions">
              <button
                type="button"
                className="btn secondary"
                disabled={tourStep === 0}
                onClick={() => setTourStep((s) => Math.max(0, s - 1))}
              >
                Précédent
              </button>
              {tourStep < TRIAL_DISCOVERY_SLIDES.length - 1 ? (
                <button type="button" className="btn" onClick={() => setTourStep((s) => s + 1)}>
                  Suivant
                </button>
              ) : (
                <Link
                  className="btn"
                  to={primaryTo}
                  onClick={() => {
                    trackProductEvent('trial_cta_clicked', { source: 'tour' })
                    setTourOpen(false)
                  }}
                >
                  Commencer mon essai
                </Link>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
