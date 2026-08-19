/**
 * Wrappers DS — cards / buttons / forms / tables / dialogs / states / motion.
 * Réutilisent le design-system ; pas de 2e skin.
 */

import type { ReactNode, TableHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import {
  Button,
  type ButtonProps,
  MetricCard,
  type MetricCardProps,
  StatCard,
  type StatCardProps,
  EmptyState,
  type EmptyStateProps,
  FormField,
  Input,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ConfirmDialog,
  cx,
} from '../../design-system'
import { MOTION_DURATION, MOTION_EASING } from '../../design-system/tokens/foundationTokens'

/* ——— Cards ——— */
export function ElfisMetricCard(props: MetricCardProps) {
  return <MetricCard {...props} className={cx('up-metric-card', props.className)} />
}

export function ElfisStatCard(props: StatCardProps) {
  return <StatCard {...props} className={cx('up-stat-card', props.className)} />
}

export function ElfisSurfaceCard({
  children,
  className,
  title,
}: {
  children: ReactNode
  className?: string
  title?: string
}) {
  return (
    <section className={cx('up-surface-card', className)} data-surface-card="v1">
      {title ? <h3 className="up-surface-card__title">{title}</h3> : null}
      {children}
    </section>
  )
}

/* ——— Buttons ——— */
export function ElfisButton(props: ButtonProps) {
  return <Button {...props} className={cx('up-btn', props.className)} />
}

export type ElfisButtonLinkProps = Omit<LinkProps, 'className'> & {
  variant?: ButtonProps['variant']
  size?: ButtonProps['size']
  className?: string
  children: ReactNode
}

/** Lien stylé comme Button DS — unifie Link.ds-btn hétérogènes. */
export function ElfisButtonLink({
  variant = 'secondary',
  size = 'md',
  className,
  children,
  ...rest
}: ElfisButtonLinkProps) {
  return (
    <Link
      className={cx(
        'btn',
        'ds-btn',
        'up-btn',
        variant === 'secondary' && 'secondary',
        variant === 'danger' && 'danger-outline',
        size === 'sm' && 'btn-sm',
        className,
      )}
      {...rest}
    >
      {children}
    </Link>
  )
}

/* ——— Forms ——— */
export function ElfisFormField(
  props: React.ComponentProps<typeof FormField>,
) {
  return <FormField {...props} className={cx('up-form-field', props.className)} />
}

/** Alias brief BRAND.ELFIS.2 — même composant que ElfisFormField. */
export const ElfisField = ElfisFormField

export function ElfisInput(props: React.ComponentProps<typeof Input>) {
  return <Input {...props} className={cx('up-input', props.className)} />
}

/* ——— Tables ——— */
export function ElfisTable({
  className,
  children,
  ...rest
}: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="up-table-wrap">
      <table className={cx('up-table', className)} data-elfis-table="v1" {...rest}>
        {children}
      </table>
    </div>
  )
}

/* ——— Dialogs ——— */
export {
  Dialog as ElfisDialog,
  DialogContent as ElfisDialogContent,
  DialogDescription as ElfisDialogDescription,
  DialogFooter as ElfisDialogFooter,
  DialogHeader as ElfisDialogHeader,
  DialogTitle as ElfisDialogTitle,
  ConfirmDialog as ElfisConfirmDialog,
}

/* ——— States ——— */
export function ElfisEmptyState(props: EmptyStateProps) {
  return <EmptyState {...props} className={cx('up-empty', props.className)} />
}

export function ElfisLoadingState({
  title = 'Chargement',
  description,
}: {
  title?: string
  description?: string
}) {
  return (
    <EmptyState
      title={title}
      description={description ?? 'Préparation de la vue…'}
      className="up-loading"
    />
  )
}

export function ElfisErrorState({
  title = 'Erreur',
  description,
  action,
}: {
  title?: string
  description?: string
  action?: ReactNode
}) {
  return (
    <EmptyState
      title={title}
      description={description}
      action={action}
      className="up-error"
    />
  )
}

/* ——— Motion ——— */
export const MotionSystem = {
  duration: MOTION_DURATION,
  easing: MOTION_EASING,
  pageEnterClass: 'up-motion-page-enter',
  fadeInClass: 'up-motion-fade-in',
} as const

export function MotionPage({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cx(MotionSystem.pageEnterClass, className)} data-motion="page-enter">
      {children}
    </div>
  )
}
