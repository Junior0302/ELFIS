import { Badge } from '../../design-system'
import { api } from '../../api'
import { CrmResourceListPage } from '../../sales/CrmResourceListPage'
import type { SalesActivityRow } from '../../sales/salesOps'

export default function SalesActivitiesPage() {
  return (
    <CrmResourceListPage<SalesActivityRow>
      title="Activités"
      description="Appels, emails, réunions, visites."
      createKind="activity"
      bulkResource="activities"
      emptyTitle="Aucune activité"
      emptyDescription="Enregistrez une activité pour alimenter le journal commercial."
      load={(token, orgId, page, q) => api.listSalesActivities(token, orgId, { page, q })}
      columns={[
        { key: 'subject', label: 'Sujet', render: (r) => r.subject },
        {
          key: 'type',
          label: 'Type',
          render: (r) => <Badge tone="accent">{r.activity_type}</Badge>,
        },
        {
          key: 'when',
          label: 'Date',
          render: (r) => new Date(r.activity_at).toLocaleString('fr-FR'),
        },
        { key: 'result', label: 'Résultat', render: (r) => r.result || '—' },
      ]}
    />
  )
}
