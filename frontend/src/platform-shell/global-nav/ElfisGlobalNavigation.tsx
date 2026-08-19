/**
 * Navigation ELFIS unique — modes sidebar (desktop) et drawer (hamburger / mobile).
 * Source : elfisNavigationConfig.
 */

import { useCallback, useMemo, type RefObject } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth'
import { getProductById } from '../../design-system'
import { ProductMark } from '../../app-launcher/ProductMark'
import { closeAllOverlays } from '../../design-system/overlays/manager/overlayLifecycle'
import { Drawer } from '../../design-system/overlays/Drawer'
import { cx } from '../../design-system'
import { ElfisIcon } from '../../unified-platform/icons/ElfisIconSystem'
import {
  ELFIS_NAV_BRAND,
  ELFIS_NAVIGATION_CONFIG,
  filterElfisNavSections,
  getFooterNavSection,
  getMainNavSections,
  isElfisNavItemActive,
  splitNavTarget,
  type ElfisNavItemConfig,
} from './elfisNavigationConfig'
import './elfis-global-navigation.css'

export const ELFIS_GLOBAL_NAV_ID = 'elfis-global-navigation'

export type ElfisGlobalNavigationMode = 'sidebar' | 'drawer'

export type ElfisGlobalNavigationProps = {
  mode: ElfisGlobalNavigationMode
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void
  onNavigate?: () => void
  className?: string
  /** Drawer only */
  open?: boolean
  onOpenChange?: (open: boolean) => void
  returnFocusRef?: RefObject<HTMLElement | null>
}

function useElfisNavPermission() {
  const { memberships, orgId } = useAuth()
  const active = memberships.find((m) => m.organization_id === orgId)
  const perms = active?.permissions ?? []
  return useCallback(
    (permission?: string) => {
      if (!permission) return true
      if (perms.includes('*')) return true
      return perms.includes(permission)
    },
    [perms],
  )
}

function useElfisNavActions(onNavigate?: () => void) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  return useCallback(
    (item: ElfisNavItemConfig) => {
      if (item.disabled) return
      if (item.action === 'logout') {
        onNavigate?.()
        closeAllOverlays('logout')
        logout()
        navigate('/login', { replace: true })
        return
      }
      if (!item.to) return
      onNavigate?.()
      closeAllOverlays('route_change')
      const { path, hash } = splitNavTarget(item.to)
      const targetPath = path || '/home'
      navigate(hash ? `${targetPath}#${hash}` : targetPath)
      if (hash) {
        requestAnimationFrame(() => {
          document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth' })
        })
      }
    },
    [logout, navigate, onNavigate],
  )
}

function NavItemRow({
  item,
  collapsed,
  active,
  onActivate,
}: {
  item: ElfisNavItemConfig
  collapsed?: boolean
  active: boolean
  onActivate: (item: ElfisNavItemConfig) => void
}) {
  const tip = collapsed || item.disabled ? item.label : undefined
  const className = cx(
    'elfis-gnav__link',
    active && 'is-active',
    item.destructive && 'elfis-gnav__link--danger',
    item.disabled && 'is-disabled',
    collapsed && 'is-collapsed',
  )

  if (item.action === 'logout') {
    return (
      <button
        type="button"
        className={className}
        title={tip}
        aria-label={collapsed ? item.label : undefined}
        disabled={item.disabled}
        onClick={() => onActivate(item)}
      >
        <span className="elfis-gnav__icon" aria-hidden>
          <ElfisIcon id={item.icon} />
        </span>
        {!collapsed ? <span className="elfis-gnav__label">{item.label}</span> : null}
      </button>
    )
  }

  // Link (pas NavLink) : le match actif est entièrement piloté par isElfisNavItemActive
  // (pathname + hash). NavLink ignore le hash et activerait tous les /home#… à la fois.
  return (
    <Link
      to={item.to || '/home'}
      className={className}
      aria-current={active ? 'page' : undefined}
      aria-label={collapsed ? item.label : undefined}
      title={tip}
      aria-disabled={item.disabled || undefined}
      onClick={(e) => {
        e.preventDefault()
        onActivate(item)
      }}
    >
      <span className="elfis-gnav__icon" aria-hidden>
        <ElfisIcon id={item.icon} />
      </span>
      {!collapsed ? (
        <>
          <span className="elfis-gnav__label">{item.label}</span>
          {item.badge ? <span className="elfis-gnav__badge">{item.badge}</span> : null}
        </>
      ) : null}
    </Link>
  )
}

function ElfisNavBody({
  mode,
  collapsed = false,
  onCollapsedChange,
  onNavigate,
  className,
}: {
  mode: ElfisGlobalNavigationMode
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void
  onNavigate?: () => void
  className?: string
}) {
  const location = useLocation()
  const platform = getProductById('elfis-core')
  const can = useElfisNavPermission()
  const activate = useElfisNavActions(onNavigate)

  const sections = useMemo(() => {
    const visible = filterElfisNavSections(ELFIS_NAVIGATION_CONFIG, can)
    return getMainNavSections(visible)
  }, [can])

  const footer = useMemo(() => {
    const visible = filterElfisNavSections(ELFIS_NAVIGATION_CONFIG, can)
    return getFooterNavSection(visible)
  }, [can])

  const hash = location.hash.replace(/^#/, '')
  const canCollapse = mode === 'sidebar' && typeof onCollapsedChange === 'function'
  const collapseLabel = collapsed ? 'Développer la navigation' : 'Réduire la navigation'

  return (
    <div
      id={mode === 'drawer' ? ELFIS_GLOBAL_NAV_ID : undefined}
      className={cx(
        'elfis-gnav',
        mode === 'sidebar' && 'elfis-gnav--sidebar',
        mode === 'drawer' && 'elfis-gnav--drawer',
        collapsed && 'is-collapsed',
        className,
      )}
      data-elfis-nav={mode}
      data-collapsed={collapsed ? 'true' : 'false'}
    >
      {mode === 'drawer' ? (
        <div className="elfis-gnav__brand elfis-gnav__brand--header">
          <ProductMark product={platform} size="sm" />
          <div>
            <strong>{ELFIS_NAV_BRAND.name}</strong>
            <span>{ELFIS_NAV_BRAND.tagline}</span>
          </div>
        </div>
      ) : null}

      {canCollapse ? (
        <div className="elfis-gnav__toolbar">
          <button
            type="button"
            className="sidebar-collapse-btn elfis-gnav__collapse"
            aria-label={collapseLabel}
            aria-expanded={!collapsed}
            title={collapseLabel}
            onClick={() => onCollapsedChange((v) => !v)}
          >
            <span className="sidebar-collapse-chevron" aria-hidden />
          </button>
        </div>
      ) : null}

      <nav
        className="elfis-gnav__nav"
        aria-label={mode === 'drawer' ? 'Menu global ELFIS' : 'Navigation plateforme'}
      >
        {sections.map((section) => (
          <section
            key={section.id}
            className="elfis-gnav__section"
            data-section={section.id}
            aria-label={section.label || undefined}
          >
            {section.label && !collapsed ? (
              <h3 className="elfis-gnav__heading">{section.label}</h3>
            ) : null}
            <ul className="elfis-gnav__list">
              {section.items.map((item) => {
                const active = isElfisNavItemActive(location.pathname, hash, item)
                return (
                  <li key={item.id}>
                    <NavItemRow
                      item={item}
                      collapsed={collapsed}
                      active={active}
                      onActivate={activate}
                    />
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
      </nav>

      <div className="elfis-gnav__footer">
        {footer ? (
          <ul className="elfis-gnav__list">
            {footer.items.map((item) => {
              const active = isElfisNavItemActive(location.pathname, hash, item)
              return (
                <li key={item.id}>
                  <NavItemRow
                    item={item}
                    collapsed={collapsed}
                    active={active}
                    onActivate={activate}
                  />
                </li>
              )
            })}
          </ul>
        ) : null}
        {!collapsed ? (
          <div className="elfis-gnav__brand">
            <ProductMark product={platform} size="sm" />
            <div>
              <strong>{ELFIS_NAV_BRAND.name}</strong>
              <span>{ELFIS_NAV_BRAND.subtitle}</span>
            </div>
          </div>
        ) : (
          <div className="elfis-gnav__brand elfis-gnav__brand--collapsed" title={ELFIS_NAV_BRAND.name}>
            <ProductMark product={platform} size="sm" />
          </div>
        )}
      </div>
    </div>
  )
}

/** Corps partagé — export pour tests / composition. */
export function ElfisGlobalNavigation(props: ElfisGlobalNavigationProps) {
  if (props.mode === 'drawer') {
    const { open = false, onOpenChange, returnFocusRef, onNavigate, className } = props
    return (
      <Drawer
        open={open}
        onOpenChange={onOpenChange ?? (() => undefined)}
        side="left"
        size="sm"
        title={ELFIS_NAV_BRAND.name}
        description={ELFIS_NAV_BRAND.tagline}
        returnFocusRef={returnFocusRef}
        className="elfis-global-nav"
        closeOnEscape
        closeOnBackdrop
      >
        <ElfisNavBody
          mode="drawer"
          onNavigate={() => {
            onOpenChange?.(false)
            onNavigate?.()
          }}
          className={className}
        />
      </Drawer>
    )
  }

  return (
    <ElfisNavBody
      mode="sidebar"
      collapsed={props.collapsed}
      onCollapsedChange={props.onCollapsedChange}
      onNavigate={props.onNavigate}
      className={props.className}
    />
  )
}

