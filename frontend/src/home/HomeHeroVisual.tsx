import { useState } from 'react'
import { HOME_HERO_VISUAL_URL } from './homeConstants'

type HomeHeroVisualProps = {
  className?: string
}

/**
 * Visual Hero Home — image manuelle + fallback monogramme « E ».
 */
export function HomeHeroVisual({ className }: HomeHeroVisualProps) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div
        className={`home-hero-visual home-hero-visual--fallback ${className ?? ''}`.trim()}
        aria-hidden
      >
        <div className="home-hero-visual__halo" />
        <svg className="home-hero-visual__orbit" viewBox="0 0 320 280" fill="none" aria-hidden>
          <ellipse cx="160" cy="140" rx="118" ry="88" stroke="currentColor" strokeOpacity="0.22" />
          <ellipse cx="160" cy="140" rx="88" ry="118" stroke="currentColor" strokeOpacity="0.14" />
          <ellipse cx="160" cy="140" rx="52" ry="52" stroke="currentColor" strokeOpacity="0.28" />
        </svg>
        <span className="home-hero-visual__mono">E</span>
      </div>
    )
  }

  return (
    <div className={`home-hero-visual ${className ?? ''}`.trim()}>
      <img
        className="home-hero-visual__img"
        src={HOME_HERO_VISUAL_URL}
        alt="ELFIS Core — environnement de travail"
        loading="lazy"
        decoding="async"
        onError={() => setFailed(true)}
      />
    </div>
  )
}
