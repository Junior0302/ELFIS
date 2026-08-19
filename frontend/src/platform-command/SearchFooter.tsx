export type SearchFooterProps = {
  hint?: string
  onOpenFullSearch?: () => void
  showFullSearch?: boolean
}

export function SearchFooter({
  hint = '↑↓ naviguer · Entrée ouvrir · Échap fermer · > commande',
  onOpenFullSearch,
  showFullSearch,
}: SearchFooterProps) {
  return (
    <footer className="cc-footer">
      <p className="cc-footer__hint">{hint}</p>
      {showFullSearch && onOpenFullSearch ? (
        <button type="button" className="cc-footer__link" onClick={onOpenFullSearch}>
          Recherche complète
        </button>
      ) : null}
    </footer>
  )
}
