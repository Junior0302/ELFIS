import type { ElementType, HTMLAttributes, ReactNode } from 'react'
import type { ContainerSize } from '../tokens/foundationTokens'
import { cx } from './cx'

export type ContainerPadding = 'none' | 'sm' | 'md' | 'lg'

export type ContainerProps = HTMLAttributes<HTMLDivElement> & {
  size?: ContainerSize
  padding?: ContainerPadding
  center?: boolean
  children: ReactNode
  as?: ElementType
}

export function Container({
  size = 'lg',
  padding = 'md',
  center = true,
  children,
  className,
  as: Comp = 'div',
  ...rest
}: ContainerProps) {
  return (
    <Comp
      className={cx(
        'ds-container',
        `ds-container--${size}`,
        `ds-container--pad-${padding}`,
        center && 'ds-container--center',
        className,
      )}
      {...rest}
    >
      {children}
    </Comp>
  )
}
