/**
 * WorkspaceSidebar — navigation métier générique (Phase 3).
 * Source : WorkspaceConfig.navigationGroups + accents CSS --workspace-*.
 */

import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { navIcons } from '../components/NavIcons'
import { cx } from '../design-system'
import {
  ProductSidebar,
  ProductSidebarFooter,
  ProductSidebarHeader,
} from '../platform-shell/ProductNavigation'
import { isWorkspaceNavLeafActive } from './registry'
import {
  filterWorkspaceLeavesByPermission,
  findActiveWorkspaceGroup,
  getVisibleWorkspaceGroups,
  workspaceGroupHasChildren,
} from './navHelpers'
import type { WorkspaceConfig, WorkspaceNavGroup, WorkspaceNavLeaf } from './types'
import './WorkspaceSidebar.css'

export type WorkspaceSidebarProps = {
  workspace: WorkspaceConfig
  navId: string
  ariaLabel: string
  collapsed: boolean
  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void
  onNavigate?: () => void
  /** Permission gate — défaut : tout autorisé. */
  can?: (permission?: string) => boolean
  /** Verrouillage trial / entitlement par groupe. */
  isGroupLocked?: (group: WorkspaceNavGroup) => boolean
  lockedMessage?: string
  onLockedActivate?: (group: WorkspaceNavGroup, el?: HTMLElement | null) => void
  /** Sur égalité de match, préférer un groupe (ex. Clients vs Prospection). */
  preferActiveGroup?: (
    best: WorkspaceNavGroup | undefined,
    candidate: WorkspaceNavGroup,
  ) => boolean
  /** Bannière au-dessus du footer (ex. toast trial). */
  banner?: ReactNode
  footer?: ReactNode
  className?: string
}

function LeafLinks({
  items,
  siblings,
  pathname,
  className,
  onNavigate,
}: {
  items: readonly WorkspaceNavLeaf[]
  siblings: readonly WorkspaceNavLeaf[]
  pathname: string
  className?: string
  onNavigate?: () => void
}) {
  return (
    <ul className={className}>
      {items.map((leaf) => {
        const active = isWorkspaceNavLeafActive(leaf, pathname, siblings)
        return (
          <li key={leaf.id}>
            <Link
              to={leaf.to}
              className={cx('nav-sublink', active && 'is-active')}
              aria-current={active ? 'page' : undefined}
              onClick={onNavigate}
              title={leaf.badge ? `${leaf.label} — ${leaf.badge}` : leaf.label}
              data-nav-leaf={leaf.id}
              data-active-policy={leaf.activePolicy ?? 'prefix'}
            >
              <span className="nav-sublink__label">{leaf.label}</span>
              {leaf.badge ? (
                <span className="nav-sublink__badge" aria-label={leaf.badge}>
                  {leaf.badge}
                </span>
              ) : null}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

export function WorkspaceSidebar({
  workspace,
  navId,
  ariaLabel,
  collapsed,
  onCollapsedChange,
  onNavigate,
  can = () => true,
  isGroupLocked,
  lockedMessage = 'Verrouillé',
  onLockedActivate,
  preferActiveGroup,
  banner,
  footer,
  className,
}: WorkspaceSidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [flyoutId, setFlyoutId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const visibleGroups = useMemo(
    () => getVisibleWorkspaceGroups(workspace, can),
    [workspace, can],
  )

  const activeGroup = useMemo(
    () => findActiveWorkspaceGroup(location.pathname, visibleGroups, preferActiveGroup),
    [location.pathname, visibleGroups, preferActiveGroup],
  )

  useEffect(() => {
    if (activeGroup && workspaceGroupHasChildren(activeGroup)) {
      setExpandedId(activeGroup.id)
    }
  }, [location.pathname, activeGroup?.id])

  useEffect(() => {
    setFlyoutId(null)
  }, [location.pathname])

  useEffect(() => {
    if (collapsed) setFlyoutId(null)
  }, [collapsed])

  const onCategoryActivate = (group: WorkspaceNavGroup) => {
    if (!workspaceGroupHasChildren(group)) {
      navigate(group.to)
      onNavigate?.()
      return
    }
    if (expandedId === group.id) {
      setExpandedId(null)
      return
    }
    setExpandedId(group.id)
    navigate(group.to)
    onNavigate?.()
  }

  const collapseLabel = collapsed ? 'Développer la navigation' : 'Réduire la navigation'
  const canCollapse = typeof onCollapsedChange === 'function'

  return (
    <ProductSidebar
      id={navId}
      label={ariaLabel}
      className={cx(
        'workspace-sidebar',
        `workspace-sidebar--${workspace.id}`,
        collapsed && 'is-collapsed',
        className,
      )}
    >
      <div
        className="workspace-sidebar__accent-scope"
        data-workspace={workspace.id}
        style={
          {
            '--workspace-accent': workspace.accent.primary,
            '--workspace-accent-soft': workspace.accent.soft,
            '--workspace-accent-dark': workspace.accent.dark,
          } as CSSProperties
        }
      >
        {canCollapse ? (
          <ProductSidebarHeader className="workspace-sidebar__toolbar">
            <button
              type="button"
              className="sidebar-collapse-btn"
              aria-label={collapseLabel}
              aria-expanded={!collapsed}
              aria-controls={navId}
              title={collapseLabel}
              onClick={() => onCollapsedChange((v) => !v)}
            >
              <span className="sidebar-collapse-chevron" aria-hidden />
            </button>
          </ProductSidebarHeader>
        ) : null}

        <div className="nav nav-categories" role="presentation">
          {visibleGroups.map((group) => {
            const Icon = navIcons[group.iconKey]
            const locked = Boolean(isGroupLocked?.(group))
            const routeActive = activeGroup?.id === group.id
            const hasChildren = workspaceGroupHasChildren(group)
            const expanded = !collapsed && expandedId === group.id && hasChildren
            const childItems = filterWorkspaceLeavesByPermission(group.children, can)
            const showFlyout = collapsed && flyoutId === group.id && hasChildren && !locked
            const tip = collapsed ? group.label : undefined

            if (locked) {
              return (
                <div key={group.id} className="nav-group" data-nav-group={group.id}>
                  <button
                    type="button"
                    className="nav-locked"
                    aria-disabled="true"
                    aria-label={`${group.label} — ${lockedMessage}`}
                    data-tooltip={lockedMessage}
                    title={tip}
                    onClick={(e) => onLockedActivate?.(group, e.currentTarget)}
                  >
                    <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                    <span className="nav-text">
                      <span className="nav-label">
                        <span className="nav-lock" aria-hidden>
                          🔒
                        </span>
                        <span>{group.label}</span>
                      </span>
                    </span>
                  </button>
                </div>
              )
            }

            if (!hasChildren) {
              return (
                <div key={group.id} className="nav-group" data-nav-group={group.id}>
                  <Link
                    to={group.to}
                    className={cx(routeActive && 'active')}
                    aria-current={routeActive ? 'page' : undefined}
                    title={tip}
                    aria-label={collapsed ? group.label : undefined}
                    onClick={onNavigate}
                  >
                    <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                    <span className="nav-text">
                      <span className="nav-label">{group.label}</span>
                    </span>
                  </Link>
                </div>
              )
            }

            return (
              <div
                key={group.id}
                className={cx(
                  'nav-group',
                  routeActive && 'is-route-active',
                  expanded && 'is-expanded',
                )}
                data-nav-group={group.id}
                onMouseEnter={() => {
                  if (collapsed) setFlyoutId(group.id)
                }}
                onMouseLeave={() => {
                  if (collapsed) setFlyoutId(null)
                }}
              >
                <button
                  type="button"
                  className={cx('nav-category-btn', routeActive && 'active')}
                  aria-expanded={expanded}
                  aria-current={routeActive ? 'true' : undefined}
                  aria-label={collapsed ? group.label : undefined}
                  title={tip}
                  onClick={() => onCategoryActivate(group)}
                >
                  <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                  <span className="nav-text">
                    <span className="nav-label">{group.label}</span>
                  </span>
                  <span className={cx('nav-chevron', expanded && 'is-open')} aria-hidden />
                </button>

                {childItems.length > 0 ? (
                  <div
                    className={cx('nav-submenu-wrap', expanded && 'is-open')}
                    aria-hidden={!expanded}
                  >
                    <LeafLinks
                      items={childItems}
                      siblings={childItems}
                      pathname={location.pathname}
                      className="nav-submenu"
                      onNavigate={onNavigate}
                    />
                  </div>
                ) : null}

                {showFlyout && childItems.length > 0 ? (
                  <div className="nav-flyout" role="menu" aria-label={group.label}>
                    <p className="nav-flyout-title">{group.label}</p>
                    <LeafLinks
                      items={childItems}
                      siblings={childItems}
                      pathname={location.pathname}
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

        {banner}
        {footer ? <ProductSidebarFooter>{footer}</ProductSidebarFooter> : null}
      </div>
    </ProductSidebar>
  )
}
