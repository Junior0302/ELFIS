import { Link } from 'react-router-dom'
import { ElfisButtonLink } from '../unified-platform'
import type { HomeSignal } from './homeSignals'

type CockpitHeroProps = {
  firstName: string
  orgName: string
  healthLabel: string
  healthOk: boolean
  signals: HomeSignal[]
  /** Date affichée — réelle (navigateur). */
  dateLabel: string
  greeting: string
}

/**
 * Header exécutif compact — Accueil plateforme.
 * Pas d’illustration orbitale ; pas de faux indicateurs.
 */
export function CockpitHero({
  firstName,
  orgName,
  healthLabel,
  healthOk,
  signals,
  dateLabel,
  greeting,
}: CockpitHeroProps) {
  const primarySignal = signals.find((s) => s.tone === 'attention') ?? signals[0]
  const attentionCount = signals.filter((s) => s.tone === 'attention').length

  return (
    <section
      className="ph-hero"
      aria-labelledby="home-welcome-title"
      data-cockpit-hero="v4"
      data-ph-hero="executive"
    >
      <div className="ph-hero__main">
        <p className="ph-hero__brand">ELFIS</p>
        <h1 id="home-welcome-title" className="ph-hero__title">
          {greeting} {firstName}
        </h1>
        <p className="ph-hero__org">
          {orgName && orgName !== '—' ? orgName : 'Organisation non sélectionnée'}
        </p>
        <p className="ph-hero__lede">
          {attentionCount > 0
            ? 'Voici ce qui mérite votre attention aujourd’hui.'
            : 'Tout est à jour — vous pouvez reprendre votre travail.'}
        </p>
        <div className="ph-hero__cta">
          <ElfisButtonLink to="#home-continue" variant="primary">
            Commencer ma journée
          </ElfisButtonLink>
          {primarySignal?.href ? (
            <ElfisButtonLink to={primarySignal.href} variant="secondary">
              Traiter l’essentiel
            </ElfisButtonLink>
          ) : (
            <ElfisButtonLink to="#home-activity" variant="secondary">
              Voir l’activité
            </ElfisButtonLink>
          )}
        </div>
      </div>
      <aside className="ph-hero__aside" aria-label="Contexte plateforme">
        <p
          className={
            healthOk ? 'ph-hero__badge ph-hero__badge--ok' : 'ph-hero__badge ph-hero__badge--warn'
          }
          role="status"
        >
          {healthLabel}
        </p>
        <p className="ph-hero__date">
          <time dateTime={new Date().toISOString().slice(0, 10)}>{dateLabel}</time>
        </p>
        {attentionCount > 0 ? (
          <p className="ph-hero__meta">
            {attentionCount} point{attentionCount > 1 ? 's' : ''} à traiter
            {primarySignal?.href ? (
              <>
                {' · '}
                <Link to={primarySignal.href}>Voir</Link>
              </>
            ) : null}
          </p>
        ) : (
          <p className="ph-hero__meta">Aucune action prioritaire</p>
        )}
      </aside>
    </section>
  )
}
