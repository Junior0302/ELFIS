import { Link } from 'react-router-dom'
import { getProductById } from '../design-system'
import { ProductMark } from '../app-launcher/ProductMark'
import { closeAllOverlays } from '../design-system/overlays/manager/overlayLifecycle'
import { cx } from '../design-system'

type PlatformBrandLockupProps = {
  className?: string
}

/**
 * Lockup ELFIS — unique contrôle permanent de retour à /home.
 * Pas de setCurrentProduct : RuntimeThemeSync suit la route.
 */
export function PlatformBrandLockup({ className }: PlatformBrandLockupProps) {
  const platform = getProductById('elfis-core')

  return (
    <Link
      to="/home"
      className={cx('ps-brand', className)}
      aria-label="Retour à ELFIS Home"
      onClick={() => closeAllOverlays('route_change')}
    >
      <ProductMark product={platform} size="sm" />
      <span className="ps-brand__name">ELFIS</span>
    </Link>
  )
}
