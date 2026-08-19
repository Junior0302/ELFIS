import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Badge, Button, Container, EmptyState, PageHeader, Section } from '../../design-system'
import type { CalendarEvent } from '../../sales/salesOps'
import '../sales/sales-workspace.css'

function startOfWeek(d: Date): Date {
  const x = new Date(d)
  const day = (x.getDay() + 6) % 7
  x.setDate(x.getDate() - day)
  x.setHours(0, 0, 0, 0)
  return x
}

export default function SalesCalendarPage() {
  const { token, orgId } = useAuth()
  const [anchor, setAnchor] = useState(() => startOfWeek(new Date()))
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'day' | 'week' | 'month'>('week')

  const range = useMemo(() => {
    const from = new Date(anchor)
    const to = new Date(anchor)
    if (view === 'day') {
      /* same day */
    } else if (view === 'week') {
      to.setDate(to.getDate() + 6)
    } else {
      from.setDate(1)
      to.setMonth(to.getMonth() + 1)
      to.setDate(0)
    }
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    return { from: fmt(from), to: fmt(to) }
  }, [anchor, view])

  useEffect(() => {
    if (!token || orgId == null) return
    setLoading(true)
    void api
      .getSalesCalendar(token, orgId, range.from, range.to)
      .then((res) => setEvents(res.events))
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Calendrier indisponible',
        )
      })
      .finally(() => setLoading(false))
  }, [token, orgId, range.from, range.to])

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title="Calendrier commercial"
        description="Rendez-vous, tâches, closings et échéances de propositions — pas de sync Google."
        actions={
          <div className="sales-deal__header-actions">
            <Button type="button" variant="secondary" onClick={() => setView('day')}>
              Jour
            </Button>
            <Button type="button" variant="secondary" onClick={() => setView('week')}>
              Semaine
            </Button>
            <Button type="button" variant="secondary" onClick={() => setView('month')}>
              Mois
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const d = new Date(anchor)
                d.setDate(d.getDate() - (view === 'month' ? 28 : view === 'week' ? 7 : 1))
                setAnchor(startOfWeek(d))
              }}
            >
              ←
            </Button>
            <Button type="button" variant="secondary" onClick={() => setAnchor(startOfWeek(new Date()))}>
              Aujourd’hui
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const d = new Date(anchor)
                d.setDate(d.getDate() + (view === 'month' ? 28 : view === 'week' ? 7 : 1))
                setAnchor(startOfWeek(d))
              }}
            >
              →
            </Button>
          </div>
        }
      />

      <Section title={`${range.from} → ${range.to}`} spacing="compact">
        {loading ? (
          <p className="muted">Chargement…</p>
        ) : error ? (
          <EmptyState title="Erreur" description={error} />
        ) : events.length === 0 ? (
          <EmptyState title="Aucun événement" description="Rien planifié sur cette période." />
        ) : (
          <ul className="sales-workspace__list">
            {events.map((ev) => (
              <li key={ev.id} className="sales-workspace__list-item">
                <header>
                  <strong>{ev.title}</strong>
                  <Badge tone="accent">{ev.event_type}</Badge>
                </header>
                <p className="muted">{new Date(ev.starts_at).toLocaleString('fr-FR')}</p>
                <Link to={ev.route} className="ds-btn btn secondary btn-sm">
                  Ouvrir
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </Container>
  )
}
