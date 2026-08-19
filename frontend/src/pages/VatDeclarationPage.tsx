import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { financialApi, formatEuro, type Kpi } from '../services/financialApi'

function currentPeriodKey(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function periodOptions(count = 12): string[] {
  const out: string[] = []
  const d = new Date()
  for (let i = 0; i < count; i += 1) {
    const y = d.getFullYear()
    const m = d.getMonth() + 1
    out.push(`${y}-${String(m).padStart(2, '0')}`)
    d.setMonth(d.getMonth() - 1)
  }
  return out
}

export default function VatDeclarationPage() {
  const { token, orgId } = useAuth()
  const [period, setPeriod] = useState(currentPeriodKey())
  const [kpis, setKpis] = useState<Kpi[]>([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [declared, setDeclared] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    try {
      const [kpiRes, periods] = await Promise.all([
        financialApi.kpis(token, orgId),
        api.listFiscalPeriods(token, orgId),
      ])
      setKpis(kpiRes.kpis)
      setDeclared(
        periods.periods.some(
          (p) => p.period_key === period && p.kind === 'vat_declaration' && p.status === 'closed',
        ),
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger la TVA')
    } finally {
      setLoading(false)
    }
  }, [token, orgId, period])

  useEffect(() => {
    void load()
  }, [load])

  const tvaEstimee = useMemo(() => {
    return kpis.find((k) => k.id === 'tva_estimee' || k.label.toLowerCase().includes('tva'))
  }, [kpis])

  const collectedHint = tvaEstimee?.hint || ''

  const markDeclared = async () => {
    if (!token || orgId == null || busy) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await api.closeFiscalPeriod(
        {
          period_key: period,
          kind: 'vat_declaration',
          notes: 'Déclaration TVA marquée comme effectuée (MVP — hors dépôt CA3 automatique).',
        },
        token,
        orgId,
      )
      setDeclared(true)
      setMessage(`Période ${period} marquée comme déclarée.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Enregistrement impossible')
    } finally {
      setBusy(false)
    }
  }

  const exportCsv = () => {
    const rows = [
      ['periode', period],
      ['tva_estimee', String(tvaEstimee?.value ?? '')],
      ['hint', collectedHint],
      ['statut_declaration', declared ? 'declaree' : 'a_faire'],
      ['note', 'KPI issus du Financial Engine — pas un formulaire CA3'],
    ]
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `tva-${period}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>TVA — préparation déclaration</h2>
          <p>
            Synthèse collectée / déductible / solde estimé pour la période. Ce n’est pas un dépôt CA3
            automatisé : exportez et déclarez sur impots.gouv, puis marquez la période comme faite.
          </p>
          <p className="muted">
            Voir aussi <Link to="/finance">Pilotage financier</Link> et{' '}
            <Link to="/cloture">Clôture de période</Link>.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="form-grid">
          <div className="field">
            <label htmlFor="vat-period">Période</label>
            <select
              id="vat-period"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
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

      {!loading && (
        <div className="stats">
          <div className="stat">
            <span>TVA estimée (solde)</span>
            <strong>{formatEuro(tvaEstimee?.value ?? 0)}</strong>
          </div>
          <div className="stat">
            <span>Statut période</span>
            <strong>{declared ? 'Déclarée' : 'À déclarer'}</strong>
          </div>
          <div className="stat">
            <span>Source</span>
            <strong>Financial Engine</strong>
          </div>
        </div>
      )}

      {collectedHint ? (
        <p className="panel muted">{collectedHint}</p>
      ) : (
        <p className="panel muted">
          Détail collectée − déductible disponible dans les KPI finance. Les montants couvrent le
          périmètre moteur actuel (pas un filtre strict mois/mois côté API KPI).
        </p>
      )}

      <section className="panel">
        <h3>Checklist déclaration</h3>
        <ul>
          <li>Vérifier les factures de vente et d’achat de la période</li>
          <li>Exporter le récapitulatif CSV</li>
          <li>Saisir / déposer la déclaration sur le portail fiscal</li>
          <li>Marquer la période comme déclarée ici</li>
        </ul>
        <div className="actions">
          <button className="btn secondary" type="button" onClick={exportCsv} disabled={loading}>
            Exporter CSV
          </button>
          <button
            className="btn"
            type="button"
            onClick={() => void markDeclared()}
            disabled={busy || declared || loading}
          >
            {declared ? 'Déjà déclarée' : 'Marquer comme déclarée'}
          </button>
        </div>
      </section>
    </>
  )
}
