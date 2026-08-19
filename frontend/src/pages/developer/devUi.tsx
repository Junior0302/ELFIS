import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

export function DevPage({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <div className="dev-page">
      <h1 className="dev-page-title">{title}</h1>
      {children}
    </div>
  )
}

export function DevUnavailable({
  title,
  reason,
}: {
  title: string
  reason: string
}) {
  return (
    <DevPage title={title}>
      <EmptyState
        title="Fonctionnalité non branchée"
        description={reason}
        action={
          <Link to="/elfadmin/developer" className="dev-btn">
            Retour vue technique
          </Link>
        }
      />
    </DevPage>
  )
}

export function DevLoading() {
  return <Skeleton rows={5} />
}

export function DevError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <ErrorState message={message} onRetry={onRetry} />
}

export function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase()
  const tone =
    s.includes('healthy') || s === 'ok' || s === 'up'
      ? 'ok'
      : s.includes('degraded') || s.includes('warn')
        ? 'warn'
        : s.includes('critical') || s.includes('unhealthy') || s.includes('fail')
          ? 'danger'
          : 'neutral'
  return <UiBadge tone={tone}>{status}</UiBadge>
}
