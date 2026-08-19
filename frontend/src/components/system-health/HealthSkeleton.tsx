export default function HealthSkeleton() {
  return (
    <div className="health-skeleton" aria-busy="true" aria-label="Chargement System Health">
      <div className="health-skeleton-block" />
      <div className="platform-stats">
        <article className="health-skeleton-block" />
        <article className="health-skeleton-block" />
        <article className="health-skeleton-block" />
        <article className="health-skeleton-block" />
      </div>
      <div className="health-skeleton-grid">
        <div className="health-skeleton-block" />
        <div className="health-skeleton-block" />
        <div className="health-skeleton-block" />
      </div>
    </div>
  )
}
