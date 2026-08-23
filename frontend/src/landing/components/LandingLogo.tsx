import { Link } from 'react-router-dom'
import { cx } from '../../design-system'

type LandingLogoProps = {
  className?: string
  /** Affiche le wordmark à côté du mark */
  withWordmark?: boolean
  size?: 'sm' | 'md' | 'lg'
}

/**
 * Marque ELFIS Core — hexagone navy, arbre vert, wordmark officiel.
 */
export function LandingLogo({ className, withWordmark = true, size = 'md' }: LandingLogoProps) {
  return (
    <Link
      to="/"
      className={cx('landing-logo', `landing-logo--${size}`, className)}
      aria-label="ELFIS Core — accueil"
    >
      <span className="landing-logo__glass">
        <img src="/elfis-core-mark.svg" alt="" width={40} height={40} decoding="async" />
      </span>
      {withWordmark ? (
        <span className="landing-logo__text">
          <strong>ELFIS Core</strong>
          <small>Plateforme</small>
        </span>
      ) : null}
    </Link>
  )
}
