/**
 * ElfisPageHeader — wrapper DS PageHeader + slots contrat Vague 2.
 */

import type { ReactNode } from 'react'
import { PageHeader, type PageHeaderProps, cx } from '../../design-system'

export type ElfisPageHeaderProps = PageHeaderProps & {
  meta?: ReactNode
  breadcrumb?: ReactNode
}

export function ElfisPageHeader({
  title,
  description,
  eyebrow,
  actions,
  children,
  meta,
  breadcrumb,
  className,
}: ElfisPageHeaderProps) {
  return (
    <PageHeader
      title={title}
      description={description}
      eyebrow={eyebrow}
      actions={actions}
      className={cx('up-page-header', className)}
    >
      {breadcrumb ? <div className="up-page-header__breadcrumb">{breadcrumb}</div> : null}
      {meta ? <div className="up-page-header__meta">{meta}</div> : null}
      {children}
    </PageHeader>
  )
}
