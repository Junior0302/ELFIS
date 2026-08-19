/**
 * ElfisPageFrame — unique source de vérité largeur / padding page.
 * Contrat : width 100%, max-width 1680px, margin auto.
 * Interdit : max-width < 1200 desktop large, fit-content, doubles containers.
 */

import type { ElementType, HTMLAttributes, ReactNode } from 'react'
import { cx } from '../../design-system'

export type ElfisPageFramePadding = 'none' | 'sm' | 'md' | 'lg' | 'comfortable'

export type ElfisPageFrameProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
  /** Densité padding — défaut comfortable (32/24/20/16 inline). */
  padding?: ElfisPageFramePadding
  as?: ElementType
}

/**
 * Frame page plateforme (1680px) — width 100%, margin auto, paddings tokens.
 * Remplace les wrappers ad hoc (PlatformPageContainer étroit, max-width locaux).
 */
export function ElfisPageFrame({
  children,
  padding = 'comfortable',
  className,
  as: Comp = 'div',
  ...rest
}: ElfisPageFrameProps) {
  const pad = padding === 'md' ? 'comfortable' : padding
  return (
    <Comp
      className={cx('up-page-frame', `up-page-frame--pad-${pad}`, className)}
      data-elfis-page-frame="v1"
      data-page-frame-padding={pad}
      data-page-frame-max="1680"
      {...rest}
    >
      {children}
    </Comp>
  )
}
