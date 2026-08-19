type Props = {
  total: number
  limit: number
  offset: number
  onPrev: () => void
  onNext: () => void
  disabled?: boolean
}

export default function AuditPagination({ total, limit, offset, onPrev, onNext, disabled }: Props) {
  const page = Math.floor(offset / limit) + 1
  const pageCount = Math.max(1, Math.ceil(total / limit))
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + limit, total)

  return (
    <nav className="audit-pagination" aria-label="Pagination audit">
      <span>
        {from}–{to} sur {total} (page {page}/{pageCount})
      </span>
      <div>
        <button type="button" className="platform-btn" disabled={disabled || offset <= 0} onClick={onPrev}>
          Précédent
        </button>
        <button
          type="button"
          className="platform-btn"
          disabled={disabled || offset + limit >= total}
          onClick={onNext}
        >
          Suivant
        </button>
      </div>
    </nav>
  )
}
