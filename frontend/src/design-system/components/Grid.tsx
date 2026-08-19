import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'
import type { GapToken } from '../tokens/foundationTokens'
import { FOUNDATION_CSS_VARS } from '../tokens/foundationTokens'
import { cx } from './cx'

export type GridColumns = 1 | 2 | 3 | 4 | 'auto-fit'

export type GridProps = HTMLAttributes<HTMLDivElement> & {
  columns?: GridColumns
  gap?: GapToken
  minItemWidth?: string
  responsive?: boolean
  children: ReactNode
}

export function Grid({
  columns = 2,
  gap = 4,
  minItemWidth = '14rem',
  responsive = true,
  className,
  style,
  children,
  ...rest
}: GridProps) {
  const merged: CSSProperties = {
    ...style,
    gap: `var(${FOUNDATION_CSS_VARS.space[gap]})`,
    ...(columns === 'auto-fit'
      ? { ['--ds-grid-min' as string]: minItemWidth }
      : {}),
  }
  return (
    <div
      className={cx(
        'ds-grid',
        columns === 'auto-fit' ? 'ds-grid--auto-fit' : `ds-grid--cols-${columns}`,
        responsive && 'ds-grid--responsive',
        className,
      )}
      style={merged}
      {...rest}
    >
      {children}
    </div>
  )
}
