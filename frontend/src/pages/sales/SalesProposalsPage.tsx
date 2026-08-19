import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  PageHeader,
  Section,
} from '../../design-system'
import { proposalPath, type ProposalListItem } from '../../sales/salesProposals'
import '../sales/sales-workspace.css'

function statusTone(status: string): 'ok' | 'accent' | 'warn' | 'danger' | 'neutral' {
  if (status === 'accepted' || status === 'converted') return 'ok'
  if (status === 'sent' || status === 'approved' || status === 'viewed') return 'accent'
  if (status === 'negotiating' || status === 'review_required') return 'warn'
  if (status === 'rejected' || status === 'expired' || status === 'cancelled') return 'danger'
  return 'neutral'
}

export default function SalesProposalsPage() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<ProposalListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    void api
      .listSalesProposals(token, orgId)
      .then((res) => setItems(res.items ?? []))
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Impossible de charger les propositions.',
        )
        setItems([])
      })
      .finally(() => setLoading(false))
  }, [token, orgId])

  useEffect(() => {
    load()
  }, [load])

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title="Propositions commerciales"
        description="Devis et offres versionnés — source de vérité backend."
        actions={
          <Link to="/sales/proposals/new" className="ds-btn btn">
            Nouvelle proposition
          </Link>
        }
      />

      {loading ? (
        <p className="muted">Chargement…</p>
      ) : error ? (
        <EmptyState
          title="Erreur"
          description={error}
          action={
            <Button type="button" onClick={load}>
              Réessayer
            </Button>
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="Aucune proposition"
          description="Créez une proposition depuis un deal ou ici."
          action={
            <Link to="/sales/proposals/new" className="ds-btn btn">
              Créer
            </Link>
          }
        />
      ) : (
        <Section title="Liste" spacing="compact">
          <ul className="sales-workspace__list">
            {items.map((p) => (
              <li key={p.id} className="sales-workspace__list-item">
                <header>
                  <strong>
                    <Link to={proposalPath(p.id)}>{p.proposal_number}</Link>
                  </strong>
                  <Badge tone={statusTone(String(p.status))}>{p.status}</Badge>
                </header>
                <p className="muted">
                  {p.proposal_type} · {p.currency}
                  {p.valid_until ? ` · validité ${p.valid_until}` : ''}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </Container>
  )
}
