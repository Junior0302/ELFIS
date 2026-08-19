/**
 * NavigationSystem — Global / Domain / ContextualSubNav via config.
 * Ne remplace pas ProductNavigation* runtime ; fournit le contrat unifié.
 */

import { NavLink } from 'react-router-dom'
import { cx } from '../../design-system'
import { ElfisIcon } from '../icons/ElfisIconSystem'
import type {
  ElfisDomainNavConfig,
  ElfisGlobalNavLink,
  ElfisNavigationItem,
  ElfisNavigationSection,
} from './types'

export type { ElfisDomainNavConfig, ElfisGlobalNavLink, ElfisNavigationItem, ElfisNavigationSection }

function itemActive(pathname: string, item: ElfisNavigationItem): boolean {
  if (item.exact) return pathname === item.href
  return pathname === item.href || pathname.startsWith(`${item.href}/`)
}

export function ElfisNavItem({
  item,
  pathname,
  collapsed,
  onNavigate,
  depth = 0,
}: {
  item: ElfisNavigationItem
  pathname: string
  collapsed?: boolean
  onNavigate?: () => void
  /** Profondeur submenu — 0 racine, 1 = nav-sublink (Compta & Sales). */
  depth?: number
}) {
  const active = itemActive(pathname, item)
  const iconId = item.icon ?? item.href
  const hasChildren = Boolean(item.children?.length)
  return (
    <div className={cx('up-nav-item-wrap', depth > 0 && 'up-nav-item-wrap--sub')} data-nav-depth={depth}>
      <NavLink
        to={item.href}
        className={cx(
          'up-nav-item',
          depth > 0 ? 'nav-sublink' : 'ps-nav-item',
          item.kind === 'switch' && 'ps-nav-item--switch',
          active && 'is-active',
          item.locked && 'is-locked',
          collapsed && 'is-collapsed',
        )}
        aria-current={active ? 'page' : undefined}
        onClick={onNavigate}
        title={collapsed ? item.label : undefined}
      >
        {depth === 0 ? (
          <span className="up-nav-item__icon" aria-hidden>
            <ElfisIcon id={iconId} />
          </span>
        ) : null}
        {!collapsed ? <span className="up-nav-item__label">{item.label}</span> : null}
        {!collapsed && item.badge ? (
          <span className="up-nav-item__badge">{item.badge}</span>
        ) : null}
      </NavLink>
      {hasChildren && !collapsed ? (
        <ul className="up-nav-submenu nav-submenu" data-nav-submenu="v1">
          {item.children!.map((child) => (
            <li key={child.id}>
              <ElfisNavItem
                item={child}
                pathname={pathname}
                collapsed={collapsed}
                onNavigate={onNavigate}
                depth={depth + 1}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

export function ElfisNavSection({
  section,
  pathname,
  collapsed,
  onNavigate,
}: {
  section: ElfisNavigationSection
  pathname: string
  collapsed?: boolean
  onNavigate?: () => void
}) {
  return (
    <div className="up-nav-section" data-nav-section={section.id}>
      {section.label && !collapsed ? (
        <p className="up-nav-section__label ps-nav-domain-hint">{section.label}</p>
      ) : null}
      <ul className="up-nav-section__list">
        {section.items.map((item) => (
          <li key={item.id}>
            <ElfisNavItem
              item={item}
              pathname={pathname}
              collapsed={collapsed}
              onNavigate={onNavigate}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Domain nav — sidebar Pilot depuis config. */
export function DomainNav({
  config,
  pathname,
  collapsed,
  onNavigate,
  className,
}: {
  config: ElfisDomainNavConfig
  pathname: string
  collapsed?: boolean
  onNavigate?: () => void
  className?: string
}) {
  return (
    <nav
      className={cx('up-domain-nav', className)}
      data-domain-nav={config.domainId}
      data-pilot={config.pilotId}
      aria-label={`Navigation ${config.domainId}`}
    >
      {config.sections.map((section) => (
        <ElfisNavSection
          key={section.id}
          section={section}
          pathname={pathname}
          collapsed={collapsed}
          onNavigate={onNavigate}
        />
      ))}
    </nav>
  )
}

/** Global links (drawer / switchers) — config only. */
export function GlobalNavLinks({
  links,
  className,
}: {
  links: ElfisGlobalNavLink[]
  className?: string
}) {
  return (
    <ul className={cx('up-global-nav-links', className)}>
      {links.map((link) => (
        <li key={link.id}>
          <NavLink to={link.href} className="up-global-nav-link">
            {link.icon ? <ElfisIcon id={link.icon} /> : null}
            {link.label}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

/** Contextual sub-nav (tabs page) — config. */
export function ContextualSubNav({
  items,
  pathname,
  className,
}: {
  items: ElfisNavigationItem[]
  pathname: string
  className?: string
}) {
  return (
    <nav className={cx('up-contextual-subnav', className)} aria-label="Sous-navigation">
      <ul className="up-contextual-subnav__list">
        {items.map((item) => {
          const active = itemActive(pathname, item)
          return (
            <li key={item.id}>
              <NavLink
                to={item.href}
                className={cx('up-contextual-subnav__item', active && 'is-active')}
                aria-current={active ? 'page' : undefined}
              >
                {item.label}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export const NavigationSystem = {
  DomainNav,
  GlobalNavLinks,
  ContextualSubNav,
  ElfisNavSection,
  ElfisNavItem,
}
