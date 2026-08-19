import { useState, type CSSProperties } from 'react'
import type { ProductIdentity } from '../design-system/types'
import { cx } from '../design-system/components/cx'

type ProductMarkProps = {
  product: ProductIdentity
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

/**
 * Identity mark — logoMark → broken fallback → initial in product accent.
 * Does not claim to be the final brand asset.
 */
export function ProductMark({ product, size = 'md', className }: ProductMarkProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const label = `Marque ${product.displayName}`
  const initial = (product.shortName || product.displayName).charAt(0).toUpperCase()
  const style = {
    '--launcher-mark-accent': product.colors.primaryColor,
  } as CSSProperties

  const src = product.branding?.logoMark || product.logoMark

  return (
    <span
      className={cx('app-launcher-mark', `app-launcher-mark--${size}`, className)}
      style={style}
      aria-label={label}
      role="img"
    >
      {src && !imgFailed ? (
        <img src={src} alt="" onError={() => setImgFailed(true)} />
      ) : (
        <span className="app-launcher-mark__fallback" aria-hidden>
          {initial}
        </span>
      )}
    </span>
  )
}
