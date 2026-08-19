import { Badge } from '../../design-system'
import { api } from '../../api'
import { CrmResourceListPage } from '../../sales/CrmResourceListPage'
import { personLabel, type SalesPerson } from '../../sales/salesOps'

export default function SalesContactsPage() {
  return (
    <CrmResourceListPage<SalesPerson>
      title="Contacts"
      description="Personnes / décideurs."
      createKind="person"
      bulkResource="people"
      emptyTitle="Aucun contact"
      emptyDescription="Créez un contact pour enrichir les relations commerciales."
      rowHref={(row) => `/sales/workspace/person/${row.id}`}
      load={(token, orgId, page, q) => api.listSalesPeople(token, orgId, { page, q })}
      onDelete={(token, orgId, id) => api.deleteSalesPerson(token, orgId, id)}
      columns={[
        { key: 'name', label: 'Nom', render: (r) => personLabel(r) },
        {
          key: 'status',
          label: 'Statut',
          render: (r) => <Badge tone="neutral">{r.status}</Badge>,
        },
        { key: 'job', label: 'Fonction', render: (r) => r.job_title || '—' },
        { key: 'email', label: 'Email', render: (r) => r.email || '—' },
      ]}
    />
  )
}
