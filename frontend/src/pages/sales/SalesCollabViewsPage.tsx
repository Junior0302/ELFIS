import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Badge, Button, Container, EmptyState, PageHeader, Section } from '../../design-system'
import '../sales/sales-workspace.css'

const VIEWS = [
  { id: 'mine', label: 'Mes éléments' },
  { id: 'team', label: 'Équipe' },
  { id: 'assigned', label: 'Assignés' },
  { id: 'following', label: 'Observés' },
  { id: 'to_review', label: 'À revoir' },
] as const

const RESOURCES = [
  { id: 'opportunities', label: 'Opportunités' },
  { id: 'leads', label: 'Leads' },
  { id: 'tasks', label: 'Tâches' },
  { id: 'proposals', label: 'Propositions' },
  { id: 'activities', label: 'Activités' },
] as const

export default function SalesCollabViewsPage() {
  const { token, orgId } = useAuth()
  const [view, setView] = useState<(typeof VIEWS)[number]['id']>('mine')
  const [resource, setResource] = useState<(typeof RESOURCES)[number]['id']>('opportunities')
  const [items, setItems] = useState<Record<string, unknown>[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    void api
      .getSalesCollabView(token, orgId, { view, resource })
      .then((res) => {
        setItems(res.items)
        setTotal(Number(res.pagination?.total ?? 0))
      })
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Vue indisponible',
        )
        setItems([])
      })
      .finally(() => setLoading(false))
  }, [token, orgId, view, resource])

  useEffect(() => {
    load()
  }, [load])

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="Commercial"
        title="Vues collaboratives"
        description="Filtres backend : mes éléments, équipe, assignés, observés, à revoir."
        actions={
          <Link to="/sales/team" className="ds-btn btn secondary">
            Tableau équipe
          </Link>
        }
      />

      <Section title="Vue" spacing="compact">
        <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
          {VIEWS.map((v) => (
            <Button
              key={v.id}
              type="button"
              size="sm"
              variant={view === v.id ? 'primary' : 'secondary'}
              onClick={() => setView(v.id)}
            >
              {v.label}
            </Button>
          ))}
        </div>
      </Section>

      {view !== 'to_review' ? (
        <Section title="Ressource" spacing="compact">
          <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
            {RESOURCES.map((r) => (
              <Button
                key={r.id}
                type="button"
                size="sm"
                variant={resource === r.id ? 'primary' : 'secondary'}
                onClick={() => setResource(r.id)}
              >
                {r.label}
              </Button>
            ))}
          </div>
        </Section>
      ) : null}

      {loading ? (
        <p className="muted">Chargement…</p>
      ) : error ? (
        <EmptyState title="Erreur" description={error} action={<Button onClick={load}>Réessayer</Button>} />
      ) : items.length === 0 ? (
        <EmptyState title="Aucun résultat" description="Aucun élément pour cette vue." />
      ) : (
        <Section title={`${total} résultat(s)`} spacing="compact">
          <ul className="sales-workspace__list">
            {items.map((row, idx) => {
              const route = typeof row.route === 'string' ? row.route : null
              const label =
                (row.title as string) ||
                (row.name as string) ||
                (row.subject as string) ||
                (row.proposal_number as string) ||
                `#${row.id ?? row.entity_id ?? idx}`
              return (
                <li key={String(row.id ?? row.entity_id ?? idx)} className="sales-workspace__list-item">
                  {route ? (
                    <Link to={route}>
                      <strong>{label}</strong>
                    </Link>
                  ) : (
                    <strong>{label}</strong>
                  )}
                  {row.status ? <Badge tone="neutral">{String(row.status)}</Badge> : null}
                </li>
              )
            })}
          </ul>
        </Section>
      )}
    </Container>
  )
}
