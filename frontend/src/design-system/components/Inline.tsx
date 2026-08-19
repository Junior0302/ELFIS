import type { CSSProperties, ElementType, HTMLAttributes, ReactNode } from 'react'
import type { GapToken } from '../tokens/foundationTokens'
import { FOUNDATION_CSS_VARS } from '../tokens/foundationTokens'
import { cx } from './cx'

type Align = 'start' | 'center' | 'end' | 'baseline' | 'stretch'
type Justify = 'start' | 'center' | 'end' | 'between' | 'around'

export type InlineProps = HTMLAttributes<HTMLElement> & {
  gap?: GapToken
  align?: Align
  justify?: Justify
  wrap?: boolean
  /** Force stack vertically below this breakpoint (CSS class). */
  stackOnMobile?: boolean
  as?: ElementType
  children: ReactNode
}

export function Inline({
  gap = 3,
  align = 'center',
  justify = 'start',
  wrap = true,
  stackOnMobile = false,
  as: Comp = 'div',
  className,
  style,
  children,
  ...rest
}: InlineProps) {
  const merged: CSSProperties = {
    ...style,
    gap: `var(${FOUNDATION_CSS_VARS.space[gap]})`,
  }
  return (
    <Comp
      className={cx(
        'ds-inline',
        `ds-inline--align-${align}`,
        `ds-inline--justify-${justify}`,
        wrap && 'ds-inline--wrap',
        stackOnMobile && 'ds-inline--stack-mobile',
        className,
      )}
      style={merged}
      {...rest}
    >
      {children}
    </Comp>
  )
}
