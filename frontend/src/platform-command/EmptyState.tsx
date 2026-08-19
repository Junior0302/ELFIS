export type EmptyStateProps = {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="cc-empty">
      <p className="cc-empty__title">{title}</p>
      {description ? <p className="cc-empty__desc">{description}</p> : null}
      {actionLabel && onAction ? (
        <button type="button" className="cc-empty__action" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}
