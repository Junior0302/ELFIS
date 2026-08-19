import { Badge } from '../../design-system'
import { api } from '../../api'
import { CrmResourceListPage } from '../../sales/CrmResourceListPage'
import type { SalesCompany } from '../../sales/salesOps'

export default function SalesCompaniesPage() {
  return (
    <CrmResourceListPage<SalesCompany>
      title="Entreprises"
      description="Fiches entreprises SalesPilot — identité commerciale. Identité partagée : ELFIS Relations."
      createKind="company"
      bulkResource="companies"
      emptyTitle="Aucune entreprise"
      emptyDescription="Ajoutez une entreprise pour rattacher contacts et opportunités."
      rowHref={(row) => `/sales/workspace/company/${row.id}`}
      load={(token, orgId, page, q) => api.listSalesCompanies(token, orgId, { page, q })}
      onDelete={(token, orgId, id) => api.deleteSalesCompany(token, orgId, id)}
      columns={[
        { key: 'name', label: 'Nom', render: (r) => r.name },
        {
          key: 'status',
          label: 'Statut',
          render: (r) => <Badge tone="neutral">{r.status}</Badge>,
        },
        { key: 'city', label: 'Ville', render: (r) => r.city || '—' },
        { key: 'email', label: 'Email', render: (r) => r.email || '—' },
      ]}
    />
  )
}
