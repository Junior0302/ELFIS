import { Link } from 'react-router-dom'
import { cx } from '../../design-system'

type LandingLogoProps = {
  className?: string
  /** Affiche le wordmark à côté du mark */
  withWordmark?: boolean
  size?: 'sm' | 'md' | 'lg'
}

/**
 * Logo officiel affiché sur la Landing.
 * Même asset que ComptaPilot / shells legacy : `/favicon.svg`.
 */
export function LandingLogo({ className, withWordmark = true, size = 'md' }: LandingLogoProps) {
  return (
    <Link
      to="/"
      className={cx('landing-logo', `landing-logo--${size}`, className)}
      aria-label="ELFIS Core — accueil"
    >
      <img src="/favicon.svg" alt="" width={40} height={40} decoding="async" />
      {withWordmark ? (
        <span className="landing-logo__text">
          <strong>ELFIS Core</strong>
          <small>Plateforme</small>
        </span>
      ) : null}
    </Link>
  )
}
