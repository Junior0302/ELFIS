/**
 * PageLayout — structure page (header + body + optional aside).
 */

import type { ReactNode } from 'react'
import { cx } from '../../design-system'
import { PlatformPageContainer } from '../PlatformPageContainer'

export type PageLayoutProps = {
  children: ReactNode
  header?: ReactNode
  aside?: ReactNode
  className?: string
  /** Si false, pas de PlatformPageContainer (déjà wrap parent). */
  contained?: boolean
  containerClassName?: string
}

export function PageLayout({
  children,
  header,
  aside,
  className,
  contained = true,
  containerClassName,
}: PageLayoutProps) {
  const body = (
    <div
      className={cx('up-page-layout', aside ? 'up-page-layout--with-aside' : undefined, className)}
      data-page-layout="v1"
    >
      {header ? <div className="up-page-layout__header">{header}</div> : null}
      <div className="up-page-layout__body">
        <div className="up-page-layout__main">{children}</div>
        {aside ? (
          <aside className="up-page-layout__aside">{aside}</aside>
        ) : null}
      </div>
    </div>
  )

  if (!contained) return body
  return (
    <PlatformPageContainer className={containerClassName}>{body}</PlatformPageContainer>
  )
}
