import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Badge, Button, Container, EmptyState, PageHeader, Section } from '../../design-system'
import type { JournalItem } from '../../sales/salesOps'

export default function SalesJournalPage() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<JournalItem[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    if (!token || orgId == null) return
    setLoading(true)
    void api
      .getSalesJournal(token, orgId, 80)
      .then((res) => setItems(res.items))
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Journal indisponible',
        )
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [token, orgId])

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="Commercial"
        title="Mon journal"
        description="Historique opérationnel — activités, tâches, notes, propositions."
        actions={
          <Button type="button" variant="secondary" onClick={load}>
            Actualiser
          </Button>
        }
      />
      <Section title="30 derniers jours" spacing="compact">
        {loading ? (
          <p className="muted">Chargement…</p>
        ) : error ? (
          <EmptyState title="Erreur" description={error} />
        ) : items.length === 0 ? (
          <EmptyState title="Journal vide" description="Aucune activité récente." />
        ) : (
          <ul className="sales-workspace__list">
            {items.map((item) => (
              <li key={item.id} className="sales-workspace__list-item">
                <header>
                  <strong>{item.title}</strong>
                  <Badge tone="neutral">{item.kind}</Badge>
                </header>
                <p className="muted">
                  {new Date(item.occurred_at).toLocaleString('fr-FR')}
                  {item.summary ? ` · ${item.summary}` : ''}
                </p>
                {item.route ? (
                  <Link to={item.route} className="ds-btn btn secondary btn-sm">
                    Ouvrir
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </Container>
  )
}
