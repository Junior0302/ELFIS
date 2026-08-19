import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import {
  categoryHasChildren,
  filterLeavesByPermission,
  findActiveCategory,
  getVisibleCategories,
  NAV_EXACT_MATCH_PATHS,
  type NavCategory,
  type NavCategoryId,
  type NavLeaf,
} from '../navModel'
import { trackProductEvent } from '../productEvents'
import { isTrialOnboardingMode } from '../subscription'
import { useSubscription } from '../subscriptionContext'
import { TRIAL_LOCK_MESSAGE } from '../trialOnboarding'
import { navIcons } from '../components/NavIcons'
import {
  ProductSidebar,
  ProductSidebarFooter,
  ProductSidebarHeader,
} from './ProductNavigation'
import { COMPTA_PRODUCT_NAV_ID } from './productSidebarCollapse'

function NavLockIcon() {
  return (
    <span className="nav-lock" aria-hidden>
      🔒
    </span>
  )
}

function LeafLinks({
  items,
  className,
  onNavigate,
}: {
  items: NavLeaf[]
  className?: string
  onNavigate?: () => void
}) {
  return (
    <ul className={className}>
      {items.map((leaf) => (
        <li key={leaf.id}>
          <NavLink
            to={leaf.to}
            end={NAV_EXACT_MATCH_PATHS.has(leaf.to)}
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

type ComptaProductNavProps = {
  onNavigate?: () => void
  collapsed: boolean
  onCollapsedChange: (collapsed: boolean | ((prev: boolean) => boolean)) => void
}

/**
 * Adapter Finance — nav métier hiérarchique dans ProductSidebar partagé.
 * Aucun chrome plateforme (org / profil / launcher).
 * Collapse contrôlé par le layout (sync grille shell).
 */
export function ComptaProductNav({
  onNavigate,
  collapsed,
  onCollapsedChange,
}: ComptaProductNavProps) {
  const { user, memberships, orgId } = useAuth()
  const { subscription, loading: subLoading } = useSubscription()
  const navigate = useNavigate()
  const location = useLocation()
  const [lockHint, setLockHint] = useState<string | null>(null)
  const [flyoutId, setFlyoutId] = useState<NavCategoryId | null>(null)
  const [expandedId, setExpandedId] = useState<NavCategoryId | null>(null)

  const activeMembership = memberships.find((m) => m.organization_id === orgId)
  const can = (permission?: string) =>
    !permission ||
    Boolean(
      activeMembership?.permissions.includes('*') ||
        activeMembership?.permissions.includes(permission),
    )

  const trialOnboarding =
    !subLoading &&
    isTrialOnboardingMode(subscription, {
      isPlatformAdmin: Boolean(user?.is_platform_admin),
    })

  const visibleCategories = useMemo(() => getVisibleCategories(can), [activeMembership])
  const activeCategory = useMemo(
    () => findActiveCategory(location.pathname),
    [location.pathname],
  )

  useEffect(() => {
    if (trialOnboarding) {
      setExpandedId(null)
      return
    }
    if (activeCategory && categoryHasChildren(activeCategory)) {
      setExpandedId(activeCategory.id)
    }
  }, [location.pathname, activeCategory?.id, trialOnboarding])

  useEffect(() => {
    setLockHint(null)
    setFlyoutId(null)
  }, [location.pathname])

  useEffect(() => {
    if (collapsed) setFlyoutId(null)
  }, [collapsed])

  const leavesFor = (category: NavCategory) => filterLeavesByPermission(category.children, can)

  const onLockedNavActivate = (label: string, to: string, el?: HTMLElement | null) => {
    trackProductEvent('locked_nav_item_clicked', { label, to })
    setLockHint(TRIAL_LOCK_MESSAGE)
    if (el) {
      el.classList.remove('nav-locked-shake')
      void el.offsetWidth
      el.classList.add('nav-locked-shake')
      window.setTimeout(() => el.classList.remove('nav-locked-shake'), 420)
    }
  }

  const onCategoryActivate = (category: NavCategory) => {
    if (!categoryHasChildren(category)) {
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

  return (
    <ProductSidebar
      id={COMPTA_PRODUCT_NAV_ID}
      label="Navigation Finance"
      className={`ps-product-nav--compta compta-product-nav${collapsed ? ' is-collapsed' : ''}`}
    >
      <ProductSidebarHeader className="compta-product-nav__toolbar">
        <button
          type="button"
          className="sidebar-collapse-btn"
          aria-label={collapseLabel}
          aria-expanded={!collapsed}
          aria-controls={COMPTA_PRODUCT_NAV_ID}
          title={collapseLabel}
          onClick={() => onCollapsedChange((v) => !v)}
        >
          <span className="sidebar-collapse-chevron" aria-hidden />
        </button>
      </ProductSidebarHeader>
      <div className="nav nav-categories" role="presentation">
        {visibleCategories.map((category) => {
          const Icon = navIcons[category.iconTo]
          const locked = trialOnboarding && category.id !== 'dashboard'
          const routeActive = activeCategory?.id === category.id
          const hasChildren = categoryHasChildren(category)
          const expanded = !collapsed && expandedId === category.id && hasChildren
          const childItems = leavesFor(category)
          const showFlyout = collapsed && flyoutId === category.id && hasChildren && !locked
          const tip = collapsed ? category.label : undefined

          if (locked) {
            return (
              <div key={category.id} className="nav-group">
                <button
                  type="button"
                  className="nav-locked"
                  aria-disabled="true"
                  aria-label={`${category.label} — ${TRIAL_LOCK_MESSAGE}`}
                  data-tooltip={TRIAL_LOCK_MESSAGE}
                  title={tip}
                  onClick={(e) => onLockedNavActivate(category.label, category.to, e.currentTarget)}
                >
                  <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                  <span className="nav-text">
                    <span className="nav-label">
                      <NavLockIcon />
                      <span>{category.label}</span>
                    </span>
                  </span>
                </button>
              </div>
            )
          }

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
                <div className={`nav-submenu-wrap${expanded ? ' is-open' : ''}`} aria-hidden={!expanded}>
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
      {lockHint ? (
        <div className="trial-nav-lock-toast" role="status">
          {lockHint}
        </div>
      ) : null}
      {user?.is_platform_admin ? (
        <ProductSidebarFooter>
          <Link to="/elfadmin" className="lan-hint sidebar-admin-link" onClick={onNavigate}>
            ELF Admin
          </Link>
        </ProductSidebarFooter>
      ) : null}
    </ProductSidebar>
  )
}

/** Exposé pour que le layout parent sache si le trial masque le chrome. */
export function useComptaTrialOnboarding(): boolean {
  const { user } = useAuth()
  const { subscription, loading } = useSubscription()
  return (
    !loading &&
    isTrialOnboardingMode(subscription, {
      isPlatformAdmin: Boolean(user?.is_platform_admin),
    })
  )
}
