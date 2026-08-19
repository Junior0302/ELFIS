import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { cx } from '../design-system'

export type ProductNavItem = {
  id: string
  label: string
  to: string
  end?: boolean
  disabled?: boolean
  locked?: boolean
}

type ProductNavigationItemProps = {
  item: ProductNavItem
  onNavigate?: () => void
  className?: string
}

/** Item de nav produit partagé — états via classes CSS, pas d’ifs productId. */
export function ProductNavigationItem({ item, onNavigate, className }: ProductNavigationItemProps) {
  if (item.disabled || item.locked) {
    return (
      <span
        className={cx(
          'ps-nav-item',
          item.disabled && 'is-disabled',
          item.locked && 'is-locked',
          className,
        )}
        aria-disabled="true"
        title={item.locked ? 'Verrouillé' : undefined}
      >
        {item.label}
      </span>
    )
  }

  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) => cx('ps-nav-item', isActive && 'is-active', className)}
      onClick={onNavigate}
    >
      {item.label}
    </NavLink>
  )
}

type ProductNavigationSectionProps = {
  title?: string
  children: ReactNode
  className?: string
}

export function ProductNavigationSection({ title, children, className }: ProductNavigationSectionProps) {
  return (
    <div className={cx('ps-nav-section', className)}>
      {title ? <p className="ps-nav-section__title">{title}</p> : null}
      <div className="ps-nav-section__items">{children}</div>
    </div>
  )
}

type ProductSidebarHeaderProps = {
  children?: ReactNode
  title?: string
  className?: string
}

export function ProductSidebarHeader({ children, title, className }: ProductSidebarHeaderProps) {
  return (
    <div className={cx('ps-product-nav__header', className)}>
      {title ? <p className="ps-product-nav__header-title">{title}</p> : null}
      {children}
    </div>
  )
}

type ProductSidebarFooterProps = {
  children: ReactNode
  className?: string
}

export function ProductSidebarFooter({ children, className }: ProductSidebarFooterProps) {
  return <div className={cx('ps-product-nav__footer', className)}>{children}</div>
}

type ProductSidebarProps = {
  children: ReactNode
  className?: string
  label?: string
  id?: string
}

/** Conteneur nav produit — différences via className / config appelant, jamais productId. */
export function ProductSidebar({ children, className, label, id }: ProductSidebarProps) {
  return (
    <nav id={id} className={cx('ps-product-nav', className)} aria-label={label ?? 'Navigation produit'}>
      {children}
    </nav>
  )
}
