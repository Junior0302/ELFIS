import { useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Badge, Button, Container, EmptyState, PageHeader, Section } from '../../design-system'
import { ConfirmDialog } from '../../design-system/overlays'

type Candidate = {
  record_id: number
  label: string
  match_level: string
  matched_on: string[]
}

export default function SalesDuplicatesPage() {
  const { token, orgId } = useAuth()
  const [resource, setResource] = useState<'leads' | 'companies' | 'people'>('companies')
  const [groups, setGroups] = useState<Candidate[][]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<{ primary: number; secondary: number } | null>(null)

  const scan = async () => {
    if (!token || orgId == null) return
    setBusy(true)
    setError('')
    try {
      const res = (await api.scanSalesDuplicates(token, orgId, resource)) as {
        groups?: Candidate[][]
      }
      setGroups(res.groups || [])
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Scan impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  const ignore = async () => {
    if (!token || orgId == null || !pending) return
    setBusy(true)
    try {
      await api.resolveSalesDuplicate(token, orgId, {
        resource,
        primary_id: pending.primary,
        secondary_id: pending.secondary,
        action: 'ignore',
      })
      setPending(null)
      await scan()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title="Revue des doublons"
        description="Détection déterministe. Aucune fusion automatique."
        actions={
          <div className="sales-deal__header-actions">
            <select value={resource} onChange={(e) => setResource(e.target.value as typeof resource)}>
              <option value="leads">Leads</option>
              <option value="companies">Entreprises</option>
              <option value="people">Contacts</option>
            </select>
            <Button type="button" variant="primary" disabled={busy} onClick={() => void scan()}>
              Scanner
            </Button>
          </div>
        }
      />
      {error ? <p role="alert">{error}</p> : null}
      <Section title="Groupes détectés" spacing="compact">
        {groups.length === 0 ? (
          <EmptyState title="Aucun doublon" description="Lancez un scan ou changez de ressource." />
        ) : (
          <ul className="sales-workspace__list">
            {groups.map((group, idx) => (
              <li key={idx} className="sales-workspace__list-item">
                {group.map((c) => (
                  <header key={c.record_id}>
                    <strong>{c.label}</strong>
                    <Badge tone={c.match_level === 'exact' ? 'warn' : 'neutral'}>{c.match_level}</Badge>
                    <span className="muted">{(c.matched_on || []).join(', ')}</span>
                  </header>
                ))}
                {group.length >= 2 ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      setPending({ primary: group[0].record_id, secondary: group[1].record_id })
                    }
                  >
                    Ignorer ce couple
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>
      <ConfirmDialog
        open={pending != null}
        onOpenChange={(o) => !o && setPending(null)}
        title="Ignorer le doublon"
        description="Aucune fusion. Le couple est journalisé comme ignoré."
        confirmLabel="Ignorer"
        tone="warning"
        loading={busy}
        onConfirm={ignore}
      />
    </Container>
  )
}
