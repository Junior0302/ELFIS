import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { financialApi } from '../services/financialApi'

function currentPeriodKey(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function periodOptions(count = 18): string[] {
  const out: string[] = []
  const d = new Date()
  for (let i = 0; i < count; i += 1) {
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
    d.setMonth(d.getMonth() - 1)
  }
  return out
}

type Checklist = {
  invoicesReviewed: boolean
  documentsProcessed: boolean
  vatPrepared: boolean
  bankSynced: boolean
}

const emptyChecklist: Checklist = {
  invoicesReviewed: false,
  documentsProcessed: false,
  vatPrepared: false,
  bankSynced: false,
}

export default function PeriodClosePage() {
  const { token, orgId } = useAuth()
  const [period, setPeriod] = useState(currentPeriodKey())
  const [checklist, setChecklist] = useState<Checklist>(emptyChecklist)
  const [notes, setNotes] = useState('')
  const [closed, setClosed] = useState(false)
  const [closedId, setClosedId] = useState<number | null>(null)
  const [docsToProcess, setDocsToProcess] = useState(0)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    try {
      const [overview, periods] = await Promise.all([
        financialApi.overview(token, orgId),
        api.listFiscalPeriods(token, orgId),
      ])
      setDocsToProcess(overview.documents_to_process || 0)
      const match = periods.periods.find(
        (p) => p.period_key === period && p.kind === 'period_close' && p.status === 'closed',
      )
      setClosed(Boolean(match))
      setClosedId(match?.id ?? null)
      if (match?.notes) setNotes(match.notes)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger la clôture')
    } finally {
      setLoading(false)
    }
  }, [token, orgId, period])

  useEffect(() => {
    void load()
  }, [load])

  const allChecked =
    checklist.invoicesReviewed &&
    checklist.documentsProcessed &&
    checklist.vatPrepared &&
    checklist.bankSynced

  const closePeriod = async () => {
    if (!token || orgId == null || busy) return
    if (!allChecked) {
      setError('Cochez toute la checklist avant de clôturer.')
      return
    }
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const res = await api.closeFiscalPeriod(
        {
          period_key: period,
          kind: 'period_close',
          notes:
            notes ||
            'Clôture manuelle MVP — pas de verrouillage des écritures / factures.',
        },
        token,
        orgId,
      )
      setClosed(true)
      setClosedId(res.period.id)
      setMessage(`Période ${period} clôturée (suivi organisationnel).`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Clôture impossible')
    } finally {
      setBusy(false)
    }
  }

  const reopen = async () => {
    if (!token || orgId == null || closedId == null || busy) return
    setBusy(true)
    setError('')
    try {
      await api.reopenFiscalPeriod(closedId, token, orgId)
      setClosed(false)
      setClosedId(null)
      setMessage(`Période ${period} rouverte.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Réouverture impossible')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Clôture de période</h2>
          <p>
            Checklist et marquage de clôture organisationnelle. MVP : pas de verrouillage technique
            des écritures ni des factures — adapté à une démo / semaine pilote.
          </p>
          <p className="muted">
            Préparez d’abord la <Link to="/tva">déclaration TVA</Link>.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="form-grid">
          <div className="field">
            <label htmlFor="close-period">Période</label>
            <select
              id="close-period"
              value={period}
              onChange={(e) => {
                setPeriod(e.target.value)
                setChecklist(emptyChecklist)
              }}
              disabled={busy}
            >
              {periodOptions().map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {loading ? <p className="loading">Chargement…</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {message ? <p className="muted">{message}</p> : null}

      <div className="stats">
        <div className="stat">
          <span>Documents à traiter</span>
          <strong>{docsToProcess}</strong>
        </div>
        <div className="stat">
          <span>Statut</span>
          <strong>{closed ? 'Clôturée' : 'Ouverte'}</strong>
        </div>
      </div>

      <section className="panel">
        <h3>Checklist clôture</h3>
        {(
          [
            ['invoicesReviewed', 'Factures de vente / paiement revues'],
            ['documentsProcessed', 'Documents OCR / propositions comptables traités'],
            ['vatPrepared', 'TVA préparée ou déclarée'],
            ['bankSynced', 'Banque synchronisée ou exclue du scope'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <input
              type="checkbox"
              checked={checklist[key]}
              disabled={busy || closed}
              onChange={(e) => setChecklist({ ...checklist, [key]: e.target.checked })}
            />
            <span>{label}</span>
          </label>
        ))}
        <div className="field" style={{ marginTop: '1rem' }}>
          <label htmlFor="close-notes">Notes</label>
          <textarea
            id="close-notes"
            rows={3}
            value={notes}
            disabled={busy || closed}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
        <div className="actions">
          {!closed ? (
            <button
              className="btn"
              type="button"
              disabled={busy || !allChecked || loading}
              onClick={() => void closePeriod()}
            >
              Clôturer la période
            </button>
          ) : (
            <button className="btn secondary" type="button" disabled={busy} onClick={() => void reopen()}>
              Rouvrir la période
            </button>
          )}
          <Link className="btn secondary" to="/tva">
            Aller à la TVA
          </Link>
        </div>
      </section>
    </>
  )
}
