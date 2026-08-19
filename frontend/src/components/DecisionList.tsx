import DecisionCard from './DecisionCard'
import type { DecisionItem } from '../decisionCenter'
import { EmptyState, ErrorState, Skeleton } from '../ui/UiStates'

type Props = {
  items: DecisionItem[]
  loading?: boolean
  error?: string
  onRetry?: () => void
  onDismiss?: (id: string) => void
  dismissingId?: string | null
  emptyTitle?: string
  emptyDescription?: string
}

export default function DecisionList({
  items,
  loading,
  error,
  onRetry,
  onDismiss,
  dismissingId,
  emptyTitle = 'Aucune décision ouverte',
  emptyDescription = 'Aucune décision ne nécessite votre attention actuellement.',
}: Props) {
  if (loading && items.length === 0) {
    return (
      <div aria-busy="true" aria-live="polite">
        <Skeleton rows={4} />
      </div>
    )
  }

  if (error && items.length === 0) {
    return <ErrorState message={error} onRetry={onRetry} />
  }

  if (items.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="decision-list" role="list">
      {error ? (
        <p className="form-error" role="alert">
          {error}{' '}
          {onRetry ? (
            <button type="button" className="linkish" onClick={onRetry}>
              Réessayer
            </button>
          ) : null}
        </p>
      ) : null}
      {items.map((item) => (
        <div key={item.id} role="listitem">
          <DecisionCard
            decision={item}
            onDismiss={onDismiss}
            dismissing={dismissingId === item.id}
          />
        </div>
      ))}
    </div>
  )
}
