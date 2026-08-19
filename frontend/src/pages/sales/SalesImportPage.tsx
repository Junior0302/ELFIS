import { useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Button, Container, EmptyState, PageHeader, Section, Stack } from '../../design-system'

export default function SalesImportPage() {
  const { token, orgId } = useAuth()
  const [resource, setResource] = useState<'leads' | 'companies' | 'people'>('leads')
  const [csv, setCsv] = useState('title,email,company_name\nExemple,demo@elfis.test,ACME')
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const [result, setResult] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const runPreview = async () => {
    if (!token || orgId == null) return
    setBusy(true)
    setError('')
    try {
      const res = await api.previewSalesImport(token, orgId, {
        resource,
        csv_text: csv,
      })
      setPreview(res)
      setResult('')
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Prévisualisation impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  const runCommit = async () => {
    if (!token || orgId == null || !preview) return
    setBusy(true)
    try {
      const rows = ((preview.rows as Array<{ status: string; data: Record<string, unknown> }>) || [])
        .filter((r) => r.status === 'ok')
        .map((r) => r.data)
      const res = await api.commitSalesImport(token, orgId, {
        resource,
        rows,
        skip_duplicates: true,
      })
      setResult(`Créés : ${res.created} · Ignorés : ${res.skipped}`)
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Import impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title="Import CSV"
        description="Simulation obligatoire avant import. Aucune fusion automatique de doublons."
      />
      <Stack gap={4}>
        <Section title="Source" spacing="compact">
          <label>
            Ressource{' '}
            <select value={resource} onChange={(e) => setResource(e.target.value as typeof resource)}>
              <option value="leads">Leads</option>
              <option value="companies">Entreprises</option>
              <option value="people">Contacts</option>
            </select>
          </label>
          <textarea
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            rows={10}
            style={{ width: '100%', marginTop: 12 }}
            aria-label="CSV"
          />
          <div className="sales-deal__header-actions">
            <Button type="button" variant="secondary" disabled={busy} onClick={() => void runPreview()}>
              Prévisualiser
            </Button>
            <Button
              type="button"
              variant="primary"
              disabled={busy || !preview}
              onClick={() => void runCommit()}
            >
              Importer les lignes OK
            </Button>
          </div>
        </Section>
        {error ? <p role="alert">{error}</p> : null}
        {result ? <p className="muted">{result}</p> : null}
        {preview ? (
          <Section title="Aperçu" spacing="compact">
            <p className="muted">
              OK {(preview as { ok_count?: number }).ok_count} · Erreurs{' '}
              {(preview as { error_count?: number }).error_count} · Doublons{' '}
              {(preview as { duplicate_count?: number }).duplicate_count}
            </p>
            <pre className="sales-workspace__note">{JSON.stringify(preview.rows, null, 2)}</pre>
          </Section>
        ) : (
          <EmptyState title="Pas encore de prévisualisation" description="Collez un CSV puis simulez." />
        )}
      </Stack>
    </Container>
  )
}
