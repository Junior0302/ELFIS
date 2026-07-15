type Props = {
  needsReview: boolean
  status?: string
}

export default function StatusBadge({ needsReview, status }: Props) {
  if (status === 'error') return <span className="badge danger">Erreur</span>
  if (status === 'processing') return <span className="badge">En cours</span>
  if (needsReview) return <span className="badge warn">À vérifier</span>
  return <span className="badge">Prêt</span>
}
