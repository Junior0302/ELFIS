import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Button, Container, EmptyState, PageHeader, Section } from '../../design-system'
import { proposalPath } from '../../sales/salesProposals'

export default function ProposalCreatePage() {
  const { token, orgId } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const opportunityId = useMemo(() => {
    const raw = params.get('opportunity_id')
    const n = raw ? Number(raw) : NaN
    return Number.isFinite(n) ? n : null
  }, [params])
  const [title, setTitle] = useState('Proposition commerciale')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const create = async () => {
    if (!token || orgId == null) return
    setBusy(true)
    setError('')
    try {
      const created = await api.createSalesProposal(token, orgId, {
        opportunity_id: opportunityId,
        proposal_type: 'quote',
        title,
        seed_from_opportunity_products: true,
        amount_source: 'final',
      })
      navigate(proposalPath(created.id))
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Création impossible.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title="Nouvelle proposition"
        description={
          opportunityId
            ? `Depuis l’opportunité #${opportunityId} — données chargées côté serveur.`
            : 'Création manuelle (quote V1).'
        }
        actions={
          <Link to="/sales/proposals" className="ds-btn btn secondary">
            Liste
          </Link>
        }
      />

      <Section title="Paramètres" spacing="compact">
        <label className="sales-workspace__meta-row">
          <span>Titre</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="ds-input"
            style={{ width: '100%', maxWidth: '28rem' }}
          />
        </label>
        <p className="muted">
          Type : quote · Les lignes issues des produits d’opportunité seront proposées au backend
          uniquement après confirmation.
        </p>
        {error ? <EmptyState title="Erreur" description={error} /> : null}
        <Button type="button" onClick={() => void create()} disabled={busy}>
          {busy ? 'Création…' : 'Confirmer la création'}
        </Button>
      </Section>
    </Container>
  )
}
