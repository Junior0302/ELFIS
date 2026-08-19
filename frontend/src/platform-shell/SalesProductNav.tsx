import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { navIcons } from '../components/NavIcons'
import {
  findActiveSalesCategory,
  salesCategoryHasChildren,
  SALES_NAV_EXACT,
  salesNavCategories,
  type SalesNavCategory,
  type SalesNavCategoryId,
  type SalesNavItem,
} from '../sales/salesNavModel'
import {
  ProductSidebar,
  ProductSidebarHeader,
} from './ProductNavigation'

export const SALES_PRODUCT_NAV_ID = 'sales-product-nav'

function LeafLinks({
  items,
  className,
  onNavigate,
}: {
  items: readonly SalesNavItem[]
  className?: string
  onNavigate?: () => void
}) {
  return (
    <ul className={className}>
      {items.map((leaf) => (
        <li key={leaf.id}>
          <NavLink
            to={leaf.to}
            end={SALES_NAV_EXACT.has(leaf.to)}
            className={({ isActive }) => `nav-sublink${isActive ? ' is-active' : ''}`}
            onClick={onNavigate}
            title={leaf.badge ? `${leaf.label} — ${leaf.badge}` : leaf.label}
          >
            <span className="nav-sublink__label">{leaf.label}</span>
            {leaf.badge ? (
              <span className="nav-sublink__badge" aria-label={leaf.badge}>
                {leaf.badge}
              </span>
            ) : null}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

type SalesProductNavProps = {
  onNavigate?: () => void
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void
}

/**
 * Adapter Commercial — même comportement nested expand que ComptaProductNav.
 * Accent bleu via tokens Pilot (--pilot-accent) ; pas de trial lock Compta.
 */
export function SalesProductNav({
  onNavigate,
  collapsed = false,
  onCollapsedChange,
}: SalesProductNavProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [flyoutId, setFlyoutId] = useState<SalesNavCategoryId | null>(null)
  const [expandedId, setExpandedId] = useState<SalesNavCategoryId | null>(null)

  const activeCategory = useMemo(
    () => findActiveSalesCategory(location.pathname),
    [location.pathname],
  )

  useEffect(() => {
    if (activeCategory && salesCategoryHasChildren(activeCategory)) {
      setExpandedId(activeCategory.id)
    }
  }, [location.pathname, activeCategory?.id])

  useEffect(() => {
    setFlyoutId(null)
  }, [location.pathname])

  useEffect(() => {
    if (collapsed) setFlyoutId(null)
  }, [collapsed])

  const onCategoryActivate = (category: SalesNavCategory) => {
    if (!salesCategoryHasChildren(category)) {
      navigate(category.to)
      onNavigate?.()
      return
    }
    if (expandedId === category.id) {
      setExpandedId(null)
      return
    }
    setExpandedId(category.id)
    navigate(category.to)
    onNavigate?.()
  }

  const collapseLabel = collapsed ? 'Développer la navigation' : 'Réduire la navigation'
  const canCollapse = typeof onCollapsedChange === 'function'

  return (
    <ProductSidebar
      id={SALES_PRODUCT_NAV_ID}
      label="Navigation Commercial"
      className={`ps-product-nav--sales sales-product-nav${collapsed ? ' is-collapsed' : ''}`}
    >
      {canCollapse ? (
        <ProductSidebarHeader className="sales-product-nav__toolbar">
          <button
            type="button"
            className="sidebar-collapse-btn"
            aria-label={collapseLabel}
            aria-expanded={!collapsed}
            aria-controls={SALES_PRODUCT_NAV_ID}
            title={collapseLabel}
            onClick={() => onCollapsedChange((v) => !v)}
          >
            <span className="sidebar-collapse-chevron" aria-hidden />
          </button>
        </ProductSidebarHeader>
      ) : null}

      <div className="nav nav-categories" role="presentation">
        {salesNavCategories.map((category) => {
          const Icon = navIcons[category.iconTo]
          const routeActive = activeCategory?.id === category.id
          const hasChildren = salesCategoryHasChildren(category)
          const expanded = !collapsed && expandedId === category.id && hasChildren
          const childItems = category.children
          const showFlyout = collapsed && flyoutId === category.id && hasChildren
          const tip = collapsed ? category.label : undefined

          if (!hasChildren) {
            return (
              <div key={category.id} className="nav-group">
                <NavLink
                  to={category.to}
                  end
                  className={({ isActive }) => (isActive ? 'active' : undefined)}
                  title={tip}
                  aria-label={collapsed ? category.label : undefined}
                  onClick={onNavigate}
                >
                  <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                  <span className="nav-text">
                    <span className="nav-label">{category.label}</span>
                  </span>
                </NavLink>
              </div>
            )
          }

          return (
            <div
              key={category.id}
              className={`nav-group${routeActive ? ' is-route-active' : ''}${
                expanded ? ' is-expanded' : ''
              }`}
              onMouseEnter={() => {
                if (collapsed) setFlyoutId(category.id)
              }}
              onMouseLeave={() => {
                if (collapsed) setFlyoutId(null)
              }}
            >
              <button
                type="button"
                className={`nav-category-btn${routeActive ? ' active' : ''}`}
                aria-expanded={expanded}
                aria-current={routeActive ? 'page' : undefined}
                aria-label={collapsed ? category.label : undefined}
                title={tip}
                onClick={() => onCategoryActivate(category)}
              >
                <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                <span className="nav-text">
                  <span className="nav-label">{category.label}</span>
                </span>
                <span className={`nav-chevron${expanded ? ' is-open' : ''}`} aria-hidden />
              </button>

              {childItems.length > 0 ? (
                <div
                  className={`nav-submenu-wrap${expanded ? ' is-open' : ''}`}
                  aria-hidden={!expanded}
                >
                  <LeafLinks items={childItems} className="nav-submenu" onNavigate={onNavigate} />
                </div>
              ) : null}

              {showFlyout && childItems.length > 0 ? (
                <div className="nav-flyout" role="menu" aria-label={category.label}>
                  <p className="nav-flyout-title">{category.label}</p>
                  <LeafLinks
                    items={childItems}
                    className="nav-flyout-list"
                    onNavigate={() => {
                      setFlyoutId(null)
                      onNavigate?.()
                    }}
                  />
                </div>
              ) : null}
            </div>
          )
        })}
      </div>

      {!collapsed ? (
        <>
          <NavLink to="/home" className="ps-nav-item ps-nav-item--switch" onClick={onNavigate}>
            ← ELFIS
          </NavLink>
          <NavLink to="/dashboard" className="ps-nav-item ps-nav-item--switch" onClick={onNavigate}>
            ← Finance
          </NavLink>
        </>
      ) : null}
    </ProductSidebar>
  )
}
