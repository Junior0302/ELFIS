import { ProductMark } from '../app-launcher/ProductMark'
import { getProductById } from '../design-system'
import { cx } from '../design-system/components/cx'

export type CommandCenterHeaderProps = {
  titleId: string
  descriptionId: string
  embedded?: boolean
}

export function CommandCenterHeader({
  titleId,
  descriptionId,
  embedded = false,
}: CommandCenterHeaderProps) {
  const platform = getProductById('elfis-core')
  return (
    <header className={cx('cc-header', embedded && 'cc-header--embedded')}>
      <div className="cc-header__brand">
        <ProductMark product={platform} size="md" />
        <div>
          <p className="cc-header__eyebrow">ELFIS Core</p>
          <p id={titleId} className="cc-header__title">
            ELFIS Command Center
          </p>
        </div>
      </div>
      <p id={descriptionId} className={cx('cc-header__subtitle', embedded && 'visually-hidden')}>
        Recherchez, naviguez ou lancez une action.
      </p>
    </header>
  )
}
