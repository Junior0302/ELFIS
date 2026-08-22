import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  Grid,
  Input,
  MetricCard,
  PageHeader,
  Section,
} from '../../design-system'
import { formatSalesMoney } from '../../sales/salesDashboard'
import type { SalesTeam, TeamDashboard } from '../../sales/salesCollab'
import '../sales/sales-workspace.css'

export default function SalesTeamDashboardPage() {
  const { token, orgId } = useAuth()
  const [teams, setTeams] = useState<SalesTeam[]>([])
  const [teamId, setTeamId] = useState<number | null>(null)
  const [data, setData] = useState<TeamDashboard | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    void Promise.all([
      api.listSalesTeams(token, orgId),
      api.getSalesTeamDashboard(token, orgId, teamId),
    ])
      .then(([t, dash]) => {
        setTeams(t)
        setData(dash)
      })
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Tableau équipe indisponible',
        )
      })
      .finally(() => setLoading(false))
  }, [token, orgId, teamId])

  useEffect(() => {
    load()
  }, [load])

  const createTeam = async () => {
    if (!token || orgId == null || !newName.trim() || busy) return
    setBusy(true)
    try {
      const team = await api.createSalesTeam(token, orgId, { name: newName.trim() })
      setNewName('')
      setTeamId(team.id)
      load()
    } finally {
      setBusy(false)
    }
  }

  if (!token || orgId == null) {
    return (
      <Container>
        <EmptyState title="Organisation requise" />
      </Container>
    )
  }

  return (
    <Container className="sales-workspace" size="xl">
      <PageHeader
        eyebrow="Commercial"
        title="Équipe commerciale"
        description="Pipeline, charge et revues — données serveur uniquement. Pas de chat."
        actions={
          <Link to="/sales/collab/views" className="ds-btn btn secondary">
            Mes vues
          </Link>
        }
      />

      <Section title="Équipes" spacing="compact">
        <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap' }}>
          <Button type="button" size="sm" variant={teamId == null ? 'primary' : 'secondary'} onClick={() => setTeamId(null)}>
            Organisation
          </Button>
          {teams.map((t) => (
            <Button
              key={t.id}
              type="button"
              size="sm"
              variant={teamId === t.id ? 'primary' : 'secondary'}
              onClick={() => setTeamId(t.id)}
            >
              {t.name}
            </Button>
          ))}
          <Input
            aria-label="Nouvelle équipe"
            placeholder="Nom équipe…"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            style={{ maxWidth: 180 }}
          />
          <Button type="button" size="sm" variant="primary" disabled={busy} onClick={() => void createTeam()}>
            Créer
          </Button>
        </div>
      </Section>

      {loading ? (
        <p className="muted">Chargement…</p>
      ) : error ? (
        <EmptyState title="Erreur" description={error} action={<Button onClick={load}>Réessayer</Button>} />
      ) : !data ? null : (
        <>
          <Section title={data.team_name || 'Organisation'} spacing="compact">
            <Grid columns={4} gap={3} responsive>
              <MetricCard title="Opportunités ouvertes" value={String(data.open_opportunities)} />
              <MetricCard title="Pipeline" value={formatSalesMoney(data.pipeline_value)} />
              <MetricCard
                title="Tâches en retard"
                value={String(data.overdue_tasks)}
                variant={data.overdue_tasks > 0 ? 'accent' : 'default'}
              />
              <MetricCard title="Revues en attente" value={String(data.pending_reviews)} />
            </Grid>
          </Section>

          <Section title="Charge par membre" spacing="compact">
            {data.load_by_member.length === 0 ? (
              <EmptyState title="Aucun membre" description="Créez une équipe et ajoutez des membres." />
            ) : (
              <ul className="sales-workspace__list">
                {data.load_by_member.map((m) => (
                  <li key={m.user_id} className="sales-workspace__list-item">
                    <strong>{m.label || `#${m.user_id}`}</strong>
                    <p className="muted">
                      Opps {m.open_opportunities} · Tâches {m.open_tasks} · Retards{' '}
                      <Badge tone={m.overdue_tasks > 0 ? 'danger' : 'neutral'}>{m.overdue_tasks}</Badge>
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Insights équipe" spacing="compact">
            {data.insights.length === 0 ? (
              <p className="muted">Aucune alerte d’équipe.</p>
            ) : (
              <ul className="sales-workspace__list">
                {data.insights.map((i) => (
                  <li key={i.title} className="sales-workspace__list-item">
                    <Badge tone={i.severity === 'high' ? 'danger' : 'warn'}>{i.severity}</Badge> {i.title}
                    <p className="muted">{i.summary}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </>
      )}
    </Container>
  )
}
