import type { ReactNode } from 'react'

export type FeatureCardProps = {
  icon: ReactNode
  title: string
  description: string
}

/** Carte feature Design System — hover CSS only. */
export function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <article className="landing-feature-card">
      <span className="landing-feature-card__icon" aria-hidden="true">
        {icon}
      </span>
      <h3 className="landing-feature-card__title">{title}</h3>
      <p className="landing-feature-card__desc">{description}</p>
    </article>
  )
}
