/**
 * Composants Insight Framework V1 — présentation uniquement.
 */

import { useId, useState, type CSSProperties, type ReactNode } from 'react'
import { cx } from '../design-system'
import { resolveInsightTone } from './tokens'
import type {
  Insight,
  InsightAction,
  InsightConfidence,
  InsightIconName,
  InsightRenderProps,
} from './types'

function confidenceLabelFr(c: InsightConfidence): string {
  if (c === 'high') return 'Élevée'
  if (c === 'medium') return 'Moyenne'
  return 'Faible'
}

export function InsightIcon({
  name,
  className,
  title,
}: {
  name: InsightIconName
  className?: string
  title?: string
}) {
  const paths: Record<InsightIconName, ReactNode> = {
    info: <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 15h-2v-6h2v6Zm0-8h-2V7h2v2Z" />,
    success: (
      <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-1.2 14.2-3.5-3.5 1.4-1.4 2.1 2.1 4.5-4.5 1.4 1.4-5.9 5.9Z" />
    ),
    attention: <path d="M1 21h22L12 2 1 21Zm12-3h-2v-2h2v2Zm0-4h-2v-4h2v4Z" />,
    critical: (
      <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 13h-2v2h2v-2Zm0-8h-2v6h2V7Z" />
    ),
    suggestion: (
      <path d="M9 21h6v-1.5H9V21Zm3-19a7 7 0 0 0-4 12.6V17h8v-2.4A7 7 0 0 0 12 2Z" />
    ),
    opportunity: (
      <path d="M12 2 9.5 8.5 3 9l5 4.5L6.5 20 12 16.5 17.5 20 16 13.5 21 9l-6.5-.5L12 2Z" />
    ),
    analysis: (
      <path d="M3 3v18h18v-2H5V3H3Zm4 12h2V9H7v6Zm4 0h2V5h-2v10Zm4 0h2v-4h-2v4Z" />
    ),
    confirmation: (
      <path d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2Zm-1 14-4-4 1.4-1.4L11 13.2l4.6-4.6L17 10l-6 6Z" />
    ),
  }
  return (
    <svg
      className={cx('elf-insight-icon', className)}
      viewBox="0 0 24 24"
      width="1.1em"
      height="1.1em"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      {paths[name]}
    </svg>
  )
}

export function InsightBadge({
  insight,
  showSeverity = false,
  className,
}: {
  insight: Insight
  showSeverity?: boolean
  className?: string
}) {
  const tone = resolveInsightTone(insight.type, insight.severity)
  return (
    <span
      className={cx(
        'elf-insight-badge',
        `elf-insight-badge--${insight.type}`,
        `elf-insight-badge--sev-${insight.severity}`,
        className,
      )}
      style={{ '--elf-insight-accent': tone.colorVar } as CSSProperties}
    >
      <InsightIcon name={tone.icon} />
      <span className="elf-insight-badge__label">
        {showSeverity ? tone.severityLabelFr : tone.labelFr}
      </span>
    </span>
  )
}

export function InsightHeader({
  insight,
  showSeverity = false,
  className,
}: {
  insight: Insight
  showSeverity?: boolean
  className?: string
}) {
  return (
    <header className={cx('elf-insight-header', className)}>
      <InsightBadge insight={insight} showSeverity={showSeverity} />
      <h4 className="elf-insight-header__title">{insight.title}</h4>
    </header>
  )
}

export function InsightFooter({
  insight,
  className,
}: {
  insight: Insight
  className?: string
}) {
  const hasSource = Boolean(insight.source?.id)
  const hasConfidence = Boolean(insight.confidence)
  const hasTs = Boolean(insight.timestamp)
  if (!hasSource && !hasConfidence && !hasTs) return null
  return (
    <footer className={cx('elf-insight-footer', className)}>
      {hasSource ? (
        <span className="elf-insight-footer__source" title={insight.source!.id}>
          {insight.source!.label || insight.source!.id}
        </span>
      ) : null}
      {hasConfidence ? (
        <span className="elf-insight-footer__confidence">
          Confiance : {confidenceLabelFr(insight.confidence!)}
        </span>
      ) : null}
      {hasTs ? (
        <time className="elf-insight-footer__time" dateTime={insight.timestamp}>
          {insight.timestamp}
        </time>
      ) : null}
    </footer>
  )
}

export function InsightActions({
  insight,
  onDismiss,
  renderAction,
  className,
}: {
  insight: Insight
  onDismiss?: (id: string) => void
  renderAction?: (action: InsightAction, insight: Insight) => ReactNode
  className?: string
}) {
  const actions = insight.actions || []
  const showDismiss = insight.dismissible && onDismiss
  if (!actions.length && !showDismiss) return null

  return (
    <div className={cx('elf-insight-actions', className)} role="group" aria-label="Actions">
      {actions.map((action) => {
        if (renderAction) {
          return (
            <span key={action.id} className="elf-insight-actions__slot">
              {renderAction(action, insight)}
            </span>
          )
        }
        if (action.href) {
          return (
            <a
              key={action.id}
              className={cx(
                'elf-insight-action',
                action.primary && 'elf-insight-action--primary',
              )}
              href={action.href}
              aria-label={action.ariaLabel || action.label}
              aria-disabled={action.disabled || undefined}
              onClick={
                action.disabled
                  ? (e) => e.preventDefault()
                  : action.onClick
                    ? (e) => {
                        e.preventDefault()
                        action.onClick?.()
                      }
                    : undefined
              }
            >
              {action.label}
            </a>
          )
        }
        return (
          <button
            key={action.id}
            type="button"
            className={cx(
              'elf-insight-action',
              action.primary && 'elf-insight-action--primary',
            )}
            disabled={action.disabled}
            aria-label={action.ariaLabel || action.label}
            onClick={action.onClick}
          >
            {action.label}
          </button>
        )
      })}
      {showDismiss ? (
        <button
          type="button"
          className="elf-insight-action elf-insight-action--ghost"
          onClick={() => onDismiss!(insight.id)}
          aria-label="Ignorer"
        >
          Ignorer
        </button>
      ) : null}
    </div>
  )
}

function WhyDetails({
  insight,
  detailsId,
}: {
  insight: Insight
  detailsId: string
}) {
  const [open, setOpen] = useState(false)
  if (!insight.details || insight.expandable === false) {
    if (insight.details && insight.expandable !== true) {
      /* details without expandable flag: show static if expandable undefined and details exist → collapsible by default */
    }
  }
  const canExpand = Boolean(insight.details) && insight.expandable !== false
  if (!insight.details) return null
  if (!canExpand) {
    return (
      <p className="elf-insight-details" id={detailsId}>
        {insight.details}
      </p>
    )
  }
  return (
    <div className="elf-insight-why">
      <button
        type="button"
        className="elf-insight-why__toggle"
        aria-expanded={open}
        aria-controls={detailsId}
        onClick={() => setOpen((v) => !v)}
      >
        Pourquoi ?
      </button>
      {open ? (
        <p className="elf-insight-details" id={detailsId}>
          {insight.details}
        </p>
      ) : null}
    </div>
  )
}

function useInsightChrome(insight: Insight) {
  const tone = resolveInsightTone(insight.type, insight.severity)
  const style = { '--elf-insight-accent': tone.colorVar } as CSSProperties
  const role = tone.defaultRole
  return { tone, style, role }
}

export function InsightCard({
  insight,
  className,
  onDismiss,
  renderAction,
  compact,
}: InsightRenderProps) {
  const baseId = useId()
  const detailsId = `${baseId}-details`
  const { style, role } = useInsightChrome(insight)
  return (
    <article
      className={cx(
        'elf-insight',
        'elf-insight--card',
        compact && 'elf-insight--compact',
        `elf-insight--${insight.type}`,
        `elf-insight--sev-${insight.severity}`,
        className,
      )}
      style={style}
      role={role}
      data-insight-id={insight.id}
      data-insight-type={insight.type}
      data-insight-severity={insight.severity}
    >
      <InsightHeader insight={insight} />
      <p className="elf-insight__summary">{insight.summary}</p>
      <WhyDetails insight={insight} detailsId={detailsId} />
      <InsightActions
        insight={insight}
        onDismiss={onDismiss}
        renderAction={renderAction}
      />
      <InsightFooter insight={insight} />
    </article>
  )
}

export function InsightInline({
  insight,
  className,
  onDismiss,
  renderAction,
}: InsightRenderProps) {
  const { style, role } = useInsightChrome(insight)
  return (
    <div
      className={cx(
        'elf-insight',
        'elf-insight--inline',
        `elf-insight--${insight.type}`,
        `elf-insight--sev-${insight.severity}`,
        className,
      )}
      style={style}
      role={role}
      data-insight-id={insight.id}
    >
      <InsightBadge insight={insight} />
      <div className="elf-insight-inline__body">
        <strong className="elf-insight-inline__title">{insight.title}</strong>
        {insight.summary !== insight.title ? (
          <span className="elf-insight-inline__summary">{insight.summary}</span>
        ) : null}
        <InsightActions
          insight={insight}
          onDismiss={onDismiss}
          renderAction={renderAction}
        />
      </div>
    </div>
  )
}

export function InsightBanner({
  insight,
  className,
  onDismiss,
  renderAction,
}: InsightRenderProps) {
  const { style, role } = useInsightChrome(insight)
  return (
    <div
      className={cx(
        'elf-insight',
        'elf-insight--banner',
        `elf-insight--${insight.type}`,
        `elf-insight--sev-${insight.severity}`,
        className,
      )}
      style={style}
      role={role}
      data-insight-id={insight.id}
    >
      <InsightIcon name={resolveInsightTone(insight.type, insight.severity).icon} />
      <div className="elf-insight-banner__text">
        <strong>{insight.title}</strong>
        <span>{insight.summary}</span>
      </div>
      <InsightActions
        insight={insight}
        onDismiss={onDismiss}
        renderAction={renderAction}
      />
    </div>
  )
}

export function InsightToast({
  insight,
  className,
  onDismiss,
  renderAction,
}: InsightRenderProps) {
  const { style } = useInsightChrome(insight)
  return (
    <div
      className={cx(
        'elf-insight',
        'elf-insight--toast',
        `elf-insight--${insight.type}`,
        className,
      )}
      style={style}
      role="status"
      aria-live="polite"
      data-insight-id={insight.id}
    >
      <InsightBadge insight={insight} />
      <p className="elf-insight-toast__msg">{insight.summary || insight.title}</p>
      <InsightActions
        insight={{ ...insight, dismissible: insight.dismissible ?? true }}
        onDismiss={onDismiss}
        renderAction={renderAction}
      />
    </div>
  )
}

export function InsightList({
  insights,
  className,
  emptyMessage = 'Aucun élément à signaler',
  variant = 'card',
  onDismiss,
  renderAction,
}: {
  insights: Insight[]
  className?: string
  emptyMessage?: string
  variant?: 'card' | 'inline'
  onDismiss?: (id: string) => void
  renderAction?: (action: InsightAction, insight: Insight) => ReactNode
}) {
  if (!insights.length) {
    return (
      <div className={cx('elf-insight-list', 'elf-insight-list--empty', className)} role="status">
        <p>{emptyMessage}</p>
      </div>
    )
  }
  const Item = variant === 'inline' ? InsightInline : InsightCard
  return (
    <ul className={cx('elf-insight-list', className)} aria-label="Insights">
      {insights.map((insight) => (
        <li key={insight.id} className="elf-insight-list__item">
          <Item
            insight={insight}
            onDismiss={onDismiss}
            renderAction={renderAction}
            compact
          />
        </li>
      ))}
    </ul>
  )
}

export function InsightStack({
  insights,
  className,
  max = 5,
  onDismiss,
  renderAction,
}: {
  insights: Insight[]
  className?: string
  max?: number
  onDismiss?: (id: string) => void
  renderAction?: (action: InsightAction, insight: Insight) => ReactNode
}) {
  const visible = insights.slice(0, max)
  return (
    <div className={cx('elf-insight-stack', className)} role="region" aria-label="Pile d’insights">
      {visible.map((insight, i) => (
        <InsightCard
          key={insight.id}
          insight={insight}
          className="elf-insight-stack__card"
          onDismiss={onDismiss}
          renderAction={renderAction}
          compact={i > 0}
        />
      ))}
    </div>
  )
}
