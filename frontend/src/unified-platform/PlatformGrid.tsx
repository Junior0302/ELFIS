import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'
import type { GapToken } from '../design-system/tokens/foundationTokens'
import { FOUNDATION_CSS_VARS } from '../design-system/tokens/foundationTokens'
import { cx } from '../design-system'

export type PlatformGridColumns = 12 | 8 | 4

export type PlatformGridProps = HTMLAttributes<HTMLDivElement> & {
  /** Grille de base — défaut 12. */
  columns?: PlatformGridColumns
  gap?: GapToken
  children: ReactNode
}

/**
 * Grille plateforme 12 / 8 / 4 colonnes (contrat Vague 1).
 * Complète ds-grid (1–4 / auto-fit) sans le remplacer.
 */
export function PlatformGrid({
  columns = 12,
  gap = 4,
  className,
  style,
  children,
  ...rest
}: PlatformGridProps) {
  const merged: CSSProperties = {
    ...style,
    gap: `var(${FOUNDATION_CSS_VARS.space[gap]})`,
  }
  return (
    <div
      className={cx('up-grid', `up-grid--cols-${columns}`, className)}
      style={merged}
      data-platform-grid="v1"
      data-columns={columns}
      {...rest}
    >
      {children}
    </div>
  )
}

export type GridItemSpan = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12

export type GridItemProps = HTMLAttributes<HTMLDivElement> & {
  span?: GridItemSpan
  /** Span ≥ md (900px). */
  spanMd?: GridItemSpan
  /** Span ≥ lg (1200px). */
  spanLg?: GridItemSpan
  children: ReactNode
}

export function GridItem({
  span = 12,
  spanMd,
  spanLg,
  className,
  style,
  children,
  ...rest
}: GridItemProps) {
  const merged: CSSProperties = {
    ...style,
    ['--up-span' as string]: String(span),
    ...(spanMd != null ? { ['--up-span-md' as string]: String(spanMd) } : {}),
    ...(spanLg != null ? { ['--up-span-lg' as string]: String(spanLg) } : {}),
  }
  return (
    <div
      className={cx(
        'up-grid-item',
        `up-grid-item--span-${span}`,
        spanMd != null && `up-grid-item--md-${spanMd}`,
        spanLg != null && `up-grid-item--lg-${spanLg}`,
        className,
      )}
      style={merged}
      data-platform-grid-item="v1"
      {...rest}
    >
      {children}
    </div>
  )
}
