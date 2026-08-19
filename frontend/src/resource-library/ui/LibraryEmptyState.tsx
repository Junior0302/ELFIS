export type LibraryEmptyStateProps = {
  title: string
  description: string
  onCreate?: () => void
  onImport?: () => void
  createDisabled?: boolean
  importDisabled?: boolean
}

export function LibraryEmptyState({
  title,
  description,
  onCreate,
  onImport,
  createDisabled,
  importDisabled,
}: LibraryEmptyStateProps) {
  return (
    <div className="sl-empty" role="status">
      <h3>{title}</h3>
      <p>{description}</p>
      <div className="sl-empty__actions">
        {onCreate ? (
          <button type="button" className="btn" disabled={createDisabled} onClick={onCreate}>
            Créer
          </button>
        ) : null}
        {onImport ? (
          <button
            type="button"
            className="btn secondary"
            disabled={importDisabled}
            onClick={onImport}
            title={importDisabled ? 'Import non implémenté en V1' : undefined}
          >
            Importer
          </button>
        ) : null}
      </div>
    </div>
  )
}
