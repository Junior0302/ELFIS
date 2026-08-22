import type { ProductId } from '../design-system'
import { getProductById } from '../design-system'
import { ProductMark } from '../app-launcher/ProductMark'
import { cx } from '../design-system'

type ProductIndicatorProps = {
  productId: ProductId
  className?: string
}

/** Libellé domaine visible — pas de signature moteur. */
const DOMAIN_CHROME: Partial<Record<ProductId, { domainLabel: string }>> = {
  comptapilot: { domainLabel: 'Finance' },
  salespilot: { domainLabel: 'Commercial' },
}

/** Mark + nom du domaine courant (accent produit, chrome plateforme). */
export function ProductIndicator({ productId, className }: ProductIndicatorProps) {
  const product = getProductById(productId)
  const domain = DOMAIN_CHROME[productId]
  const title = domain?.domainLabel ?? product.displayName
  const subtitle = domain ? null : 'by ELFIS'

  return (
    <div className={cx('ps-product', className)} data-product={productId}>
      <ProductMark product={product} size="sm" />
      <div className="ps-product__text">
        <strong>{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
    </div>
  )
}
