import type { ElementType, HTMLAttributes, ReactNode } from 'react'
import { Container, type ContainerPadding } from '../design-system'
import type { ContainerSize } from '../design-system/tokens/foundationTokens'
import { cx } from '../design-system'
import { isUnifiedPlatformUiEnabled } from './featureFlag'

export type PlatformPageContainerProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
  /** Défaut xl (1200) — tokens plateforme. */
  size?: ContainerSize
  padding?: ContainerPadding
  as?: ElementType
}

/**
 * Conteneur page unifié — max-width + paddings tokens.
 * Réutilise ds-container ; ajoute classes up-page pour le contrat Vague 1.
 */
export function PlatformPageContainer({
  children,
  size = 'xl',
  padding = 'md',
  className,
  as,
  ...rest
}: PlatformPageContainerProps) {
  const unified = isUnifiedPlatformUiEnabled()
  return (
    <Container
      as={as}
      size={size}
      padding={padding}
      center
      className={cx('up-page', unified && 'up-page--unified', className)}
      data-platform-page-container="v1"
      {...rest}
    >
      {children}
    </Container>
  )
}
