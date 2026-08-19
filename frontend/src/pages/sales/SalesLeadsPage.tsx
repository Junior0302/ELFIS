import { Badge } from '../../design-system'
import { api } from '../../api'
import { CrmResourceListPage } from '../../sales/CrmResourceListPage'
import type { SalesLead } from '../../sales/salesOps'

export default function SalesLeadsPage() {
  return (
    <CrmResourceListPage<SalesLead>
      title="Leads"
      description="Prospects commerciaux — CRUD complet, filtres et actions groupées."
      createKind="lead"
      bulkResource="leads"
      emptyTitle="Aucun lead"
      emptyDescription="Créez un lead pour démarrer le pipeline commercial."
      rowHref={(row) => `/sales/workspace/lead/${row.id}`}
      load={(token, orgId, page, q) => api.listSalesLeads(token, orgId, { page, q })}
      onDelete={(token, orgId, id) => api.deleteSalesLead(token, orgId, id)}
      columns={[
        { key: 'title', label: 'Titre', render: (r) => r.title },
        {
          key: 'status',
          label: 'Statut',
          render: (r) => <Badge tone="neutral">{r.status}</Badge>,
        },
        { key: 'company', label: 'Entreprise', render: (r) => r.company_name || '—' },
        { key: 'email', label: 'Email', render: (r) => r.email || '—' },
      ]}
    />
  )
}
