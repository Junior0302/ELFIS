import type { CommandResultGroup, CommandResultItem } from './commandTypes'
import type { CommandSearchStatus } from './commandTypes'
import { ResultGroup } from './ResultGroup'
import { EmptyState } from './EmptyState'

export type CommandResultsProps = {
  groups: CommandResultGroup[]
  flatItems: CommandResultItem[]
  activeId: string | null
  status: CommandSearchStatus
  errorMessage?: string | null
  query: string
  commandMode: boolean
  itemDomId: (itemId: string) => string
  onSelect: (item: CommandResultItem) => void
  onHover: (itemId: string) => void
  onRetry?: () => void
  onOpenFullSearch?: () => void
}

export function CommandResults({
  groups,
  flatItems,
  activeId,
  status,
  errorMessage,
  query,
  commandMode,
  itemDomId,
  onSelect,
  onHover,
  onRetry,
  onOpenFullSearch,
}: CommandResultsProps) {
  if (status === 'loading' && groups.length === 0) {
    return (
      <div className="cc-results" role="status" aria-live="polite" aria-busy="true">
        <p className="cc-results__hint">Recherche en cours…</p>
        <ul className="cc-skeleton" aria-hidden>
          <li />
          <li />
          <li />
        </ul>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="cc-results" role="alert">
        <EmptyState
          title="Impossible de rechercher"
          description={errorMessage || 'Une erreur est survenue.'}
          actionLabel="Réessayer"
          onAction={onRetry}
        />
      </div>
    )
  }

  if (flatItems.length === 0 && query.trim()) {
    return (
      <div className="cc-results" role="status" aria-live="polite" id="cc-results-listbox">
        <EmptyState
          title={commandMode ? 'Aucune commande correspondante' : 'Aucun résultat'}
          description={
            commandMode
              ? 'Essayez « nouvelle facture », « ouvrir salespilot » ou « importer document ».'
              : 'Affinez votre requête ou ouvrez la recherche complète.'
          }
          actionLabel={!commandMode ? 'Ouvrir la recherche ELFIS' : undefined}
          onAction={!commandMode ? onOpenFullSearch : undefined}
        />
      </div>
    )
  }

  return (
    <div
      className="cc-results"
      role="listbox"
      id="cc-results-listbox"
      aria-label="Résultats du Command Center"
    >
      {status === 'loading' ? (
        <p className="cc-results__hint" role="status" aria-live="polite">
          Mise à jour…
        </p>
      ) : null}
      {groups.map((g) => (
        <ResultGroup
          key={g.id}
          group={g}
          activeId={activeId}
          itemDomId={itemDomId}
          onSelect={onSelect}
          onHover={onHover}
        />
      ))}
    </div>
  )
}
