import { Badge } from '../../design-system'
import { api } from '../../api'
import { CrmResourceListPage } from '../../sales/CrmResourceListPage'
import type { SalesTaskRow } from '../../sales/salesOps'

export default function SalesTasksPage() {
  return (
    <CrmResourceListPage<SalesTaskRow>
      title="Tâches"
      description="Actions commerciales à suivre."
      contextLabel="Commercial · Activité"
      createKind="task"
      bulkResource="tasks"
      emptyTitle="Aucune tâche"
      emptyDescription="Planifiez une tâche pour structurer la journée commerciale."
      load={(token, orgId, page, q) => api.listSalesTasks(token, orgId, { page, q })}
      onDelete={(token, orgId, id) => api.deleteSalesTask(token, orgId, id)}
      columns={[
        { key: 'title', label: 'Titre', render: (r) => r.title },
        {
          key: 'status',
          label: 'Statut',
          render: (r) => <Badge tone={r.status === 'done' ? 'ok' : 'warn'}>{r.status}</Badge>,
        },
        {
          key: 'priority',
          label: 'Priorité',
          render: (r) => <Badge tone={r.priority === 'high' ? 'danger' : 'neutral'}>{r.priority}</Badge>,
        },
        {
          key: 'due',
          label: 'Échéance',
          render: (r) => (r.due_at ? new Date(r.due_at).toLocaleString('fr-FR') : '—'),
        },
      ]}
    />
  )
}
