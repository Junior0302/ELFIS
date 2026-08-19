import type { CSSProperties, ElementType, HTMLAttributes, ReactNode } from 'react'
import type { GapToken } from '../tokens/foundationTokens'
import { FOUNDATION_CSS_VARS } from '../tokens/foundationTokens'
import { cx } from './cx'

type Align = 'start' | 'center' | 'end' | 'stretch'
type Justify = 'start' | 'center' | 'end' | 'between' | 'around'

export type StackProps = HTMLAttributes<HTMLElement> & {
  gap?: GapToken
  align?: Align
  justify?: Justify
  as?: ElementType
  children: ReactNode
}

export function Stack({
  gap = 4,
  align = 'stretch',
  justify = 'start',
  as: Comp = 'div',
  className,
  style,
  children,
  ...rest
}: StackProps) {
  const merged: CSSProperties = {
    ...style,
    gap: `var(${FOUNDATION_CSS_VARS.space[gap]})`,
  }
  return (
    <Comp
      className={cx(
        'ds-stack',
        `ds-stack--align-${align}`,
        `ds-stack--justify-${justify}`,
        className,
      )}
      style={merged}
      {...rest}
    >
      {children}
    </Comp>
  )
}
