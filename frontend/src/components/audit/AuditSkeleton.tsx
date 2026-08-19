export default function AuditSkeleton() {
  return (
    <div className="audit-skeleton" aria-busy="true" aria-label="Chargement Activity Center">
      <div className="health-skeleton-block" />
      <div className="platform-stats">
        <article className="health-skeleton-block" />
        <article className="health-skeleton-block" />
        <article className="health-skeleton-block" />
        <article className="health-skeleton-block" />
      </div>
      <div className="health-skeleton-block" style={{ minHeight: '12rem' }} />
    </div>
  )
}
