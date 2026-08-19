import type { AuditStatistics } from '../../types/audit'

export default function AuditSummaryCards({ stats }: { stats: AuditStatistics }) {
  const cards = [
    { label: `Événements (${stats.hours}h)`, value: stats.total },
    { label: 'Échecs', value: stats.failure },
    { label: 'Avertissements & erreurs', value: stats.warnings_errors },
    { label: 'Permissions refusées', value: stats.permission_denied },
    { label: 'Échecs de connexion', value: stats.login_failure },
    { label: 'Changements IAM', value: stats.iam_changes },
  ]
  return (
    <div className="platform-stats audit-summary-cards" role="region" aria-label="Synthèse audit">
      {cards.map((card) => (
        <article key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </article>
      ))}
    </div>
  )
}
