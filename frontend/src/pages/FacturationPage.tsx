import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, formatEuro, type BillingOverview, type SalesDoc } from '../api'
import { useAuth } from '../auth'
import { DocumentCreateFlow } from '../comptapilot/facturation/DocumentCreateFlow'
import '../comptapilot/facturation/facturation-spaces.css'
import FirstActionSuccessPanel from '../components/FirstActionSuccessPanel'
import InvoicePaymentModal from '../components/InvoicePaymentModal'
import SalesDocLinesEditor from '../components/SalesDocLinesEditor'
import SalesDocPreviewModal from '../components/SalesDocPreviewModal'
import {
  facturationPageCopy,
  invoiceSuccessActions,
  isLaunchDashboardSource,
  markLaunchDashboardStale,
  withLaunchSource,
  type FirstExperienceAction,
} from '../firstExperience'
import type { LaunchDashboardData } from '../launchDashboard'
import {
  emptySalesLine,
  linesTotalHt,
  normalizeSalesLines,
  salesLinesFromDoc,
  type SalesLineDraft,
} from '../salesDocLines'
import { buildDuplicateSalesDocPayload } from '../salesDocDuplicate'
import { EmptyState } from '../ui/UiStates'
import '../comptapilot/facturation/facturation-premium.css'

const emptyForm = {
  doc_type: 'facture',
  customer_name: '',
  customer_email: '',
  customer_id: null as number | null,
  vat_rate: 20,
  notes: '',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  sent: 'Envoyé',
  accepted: 'Accepté',
  refused: 'Refusé',
  partial: 'Partiel',
  paid: 'Payé',
  overdue: 'En retard',
  cancelled: 'Annulé',
}

const TYPE_LABELS: Record<string, string> = {
  devis: 'Devis',
  facture: 'Facture',
  avoir: 'Avoir',
}

function statusBadgeClass(status: string) {
  if (status === 'paid' || status === 'accepted') return 'badge ok'
  if (status === 'overdue' || status === 'refused') return 'badge danger'
  if (status === 'sent' || status === 'partial') return 'badge warn'
  return 'badge'
}

export default function FacturationPage() {
  const { token, orgId } = useAuth()
  const [searchParams] = useSearchParams()
  const fromLaunch = isLaunchDashboardSource(searchParams.get('source'))
  const prefillCustomerIdRaw = searchParams.get('customer_id')
  const prefillCustomerId = prefillCustomerIdRaw ? Number(prefillCustomerIdRaw) : null
  const openDocIdRaw = searchParams.get('doc')
  const openDocId = openDocIdRaw ? Number(openDocIdRaw) : null

  const [data, setData] = useState<BillingOverview | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [lines, setLines] = useState<SalesLineDraft[]>([emptySalesLine()])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [previewDoc, setPreviewDoc] = useState<SalesDoc | null>(null)
  const [payDoc, setPayDoc] = useState<SalesDoc | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [typeFilter, setTypeFilter] = useState<'all' | 'devis' | 'facture' | 'avoir'>('all')
  const [createdDoc, setCreatedDoc] = useState<SalesDoc | null>(null)
  const [successPrimary, setSuccessPrimary] = useState<FirstExperienceAction | null>(null)
  const [successSecondary, setSuccessSecondary] = useState<FirstExperienceAction[]>([])
  const [prefillError, setPrefillError] = useState('')
  const [prefillApplied, setPrefillApplied] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(
    () => searchParams.get('create') === '1',
  )
  const createTriggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (searchParams.get('create') === '1') {
      setCreateDialogOpen(true)
    }
  }, [searchParams])

  const load = () => {
    if (!token) return
    api
      .billingOverview(token, orgId)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Erreur facturation'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  useEffect(() => {
    if (!token || orgId == null || !openDocId || Number.isNaN(openDocId)) return
    if (previewDoc?.id === openDocId) return
    let cancelled = false
    void api
      .getSalesDoc(openDocId, token, orgId)
      .then((payload) => {
        if (!cancelled) setPreviewDoc(payload.document)
      })
      .catch(() => {
        /* ignore — list still usable */
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId, openDocId, previewDoc?.id])

  useEffect(() => {
    if (!token || orgId == null || !prefillCustomerId || Number.isNaN(prefillCustomerId)) return
    if (prefillApplied) return
    let cancelled = false
    const apply = async () => {
      try {
        const fromOverview = data?.customers.find((c) => c.id === prefillCustomerId)
        const customer =
          fromOverview || (await api.getCustomer(prefillCustomerId, token, orgId))
        if (cancelled) return
        setForm((current) => ({
          ...current,
          doc_type: 'facture',
          customer_id: customer.id,
          customer_name: customer.name,
          customer_email: customer.email || '',
        }))
        setPrefillError('')
        setPrefillApplied(true)
      } catch (e) {
        if (cancelled) return
        setPrefillError(
          e instanceof Error
            ? e.message
            : 'Client introuvable ou inaccessible pour cette organisation.',
        )
        setPrefillApplied(true)
      }
    }
    void apply()
    return () => {
      cancelled = true
    }
  }, [token, orgId, prefillCustomerId, data, prefillApplied])

  const fillFromCustomerName = (name: string) => {
    const customer = data?.customers.find((c) => c.name === name)
    setForm((current) => ({
      ...current,
      customer_name: name,
      customer_id: customer?.id ?? null,
      customer_email: customer?.email || current.customer_email,
    }))
  }

  const startEdit = (doc: SalesDoc) => {
    setEditingId(doc.id)
    setPreviewDoc(null)
    setCreatedDoc(null)
    setForm({
      doc_type: doc.doc_type,
      customer_name: doc.customer_name,
      customer_email: doc.customer_email || '',
      customer_id: null,
      vat_rate: doc.vat_rate,
      notes: doc.notes || '',
    })
    setLines(salesLinesFromDoc(doc.lines, doc.amount_ht))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
    setLines([emptySalesLine()])
  }

  const buildInvoiceSuccess = async (doc: SalesDoc) => {
    let launch: LaunchDashboardData | null = null
    if (token && orgId != null) {
      try {
        launch = await api.getLaunchDashboard(token, orgId)
      } catch {
        launch = null
      }
    }
    const next = invoiceSuccessActions(launch)
    const secondary: FirstExperienceAction[] = [
      {
        label: 'Voir la facture',
        onClick: () => setPreviewDoc(doc),
        tone: 'secondary',
      },
      {
        label: 'Télécharger le PDF',
        onClick: () => {
          if (!token || orgId == null) return
          void api.downloadSalesDocPdf(doc.id, token, orgId).catch((err) => {
            setError(err instanceof Error ? err.message : 'Téléchargement impossible')
          })
        },
        tone: 'secondary',
      },
      {
        label: 'Envoyer la facture',
        onClick: () => setPreviewDoc(doc),
        tone: 'secondary',
      },
      ...next.secondary,
    ]
    const seen = new Set<string>([next.primary.label])
    setSuccessPrimary(next.primary)
    setSuccessSecondary(
      secondary.filter((a) => {
        if (seen.has(a.label)) return false
        seen.add(a.label)
        return true
      }),
    )
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return
    setMessage('')
    setError('')
    setCreatedDoc(null)
    const normalized = normalizeSalesLines(lines)
    if (normalized.length === 0) {
      setError('Ajoutez au moins une ligne avec une désignation.')
      return
    }
    const amount_ht = linesTotalHt(normalized)
    setSubmitting(true)
    try {
      if (editingId) {
        await api.updateSalesDoc(
          editingId,
          {
            customer_name: form.customer_name,
            customer_email: form.customer_email,
            customer_id: form.customer_id,
            amount_ht,
            vat_rate: form.vat_rate,
            notes: form.notes,
            lines: normalized,
          },
          token,
          orgId,
        )
        setMessage('Document mis à jour.')
        resetForm()
      } else {
        const created = await api.createSalesDoc(
          { ...form, amount_ht, lines: normalized },
          token,
          orgId,
        )
        markLaunchDashboardStale()
        setMessage(`${TYPE_LABELS[created.doc_type] || created.doc_type} ${created.number} créé.`)
        setPreviewDoc(created)
        setCreatedDoc(created)
        resetForm()
        await buildInvoiceSuccess(created)
      }
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enregistrement impossible')
    } finally {
      setSubmitting(false)
    }
  }

  const visualize = (doc: SalesDoc) => {
    setPreviewDoc(doc)
  }

  const remove = async (doc: SalesDoc) => {
    const label =
      doc.doc_type === 'devis' ? 'ce devis' : doc.doc_type === 'avoir' ? 'cet avoir' : 'cette facture'
    const confirmed = window.confirm(
      `Supprimer ${label} ${doc.number} ?\n\nClient : ${doc.customer_name}\nMontant TTC : ${formatEuro(doc.amount_ttc)}\n\nCette action est définitive.`,
    )
    if (!confirmed) return
    setBusyId(doc.id)
    setMessage('')
    setError('')
    try {
      await api.deleteSalesDoc(doc.id, token, orgId)
      setMessage(`${doc.number} supprimé.`)
      if (editingId === doc.id) resetForm()
      if (previewDoc?.id === doc.id) setPreviewDoc(null)
      if (createdDoc?.id === doc.id) setCreatedDoc(null)
      markLaunchDashboardStale()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
    } finally {
      setBusyId(null)
    }
  }

  const act = async (doc: SalesDoc, action: string, body?: object) => {
    setBusyId(doc.id)
    setMessage('')
    setError('')
    try {
      await api.billingAction(doc.id, action, token, orgId, body)
      setMessage(`Action effectuée sur ${doc.number}.`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible')
    } finally {
      setBusyId(null)
    }
  }

  const duplicate = async (doc: SalesDoc) => {
    setBusyId(doc.id)
    setMessage('')
    setError('')
    try {
      const created = await api.createSalesDoc(buildDuplicateSalesDocPayload(doc), token, orgId)
      setMessage(`${TYPE_LABELS[created.doc_type] || created.doc_type} ${created.number} créé (copie de ${doc.number}).`)
      startEdit(created)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Duplication impossible')
    } finally {
      setBusyId(null)
    }
  }

  const submitPayment = async (payload: {
    amount: number
    method: string
    reference: string
    paid_at?: string
  }) => {
    if (!payDoc) return
    setBusyId(payDoc.id)
    setMessage('')
    setError('')
    try {
      await api.billingAction(payDoc.id, 'pay', token, orgId, payload)
      setMessage(`Paiement enregistré sur ${payDoc.number}.`)
      setPayDoc(null)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Paiement impossible')
    } finally {
      setBusyId(null)
    }
  }

  if (error && !data) return <div className="panel form-error">{error}</div>
  if (!data) return <div className="loading">Chargement facturation…</div>

  const documents =
    typeFilter === 'all'
      ? data.documents
      : data.documents.filter((doc) => doc.doc_type === typeFilter)
  const invoiceCount = data.documents.filter((d) => d.doc_type === 'facture').length
  const copy = facturationPageCopy({ fromLaunch, hasInvoices: invoiceCount > 0 })
  const formTitle = editingId ? 'Modifier le document' : copy.formTitle

  const pageTitle =
    fromLaunch && invoiceCount === 0 ? 'Créer votre première facture' : 'Facturation'
  const pageLede = fromLaunch
    ? copy.formLead
    : 'Créez et pilotez vos documents commerciaux'
  const unpaidEmphasis = data.stats.unpaid > 0 || data.stats.unpaid_amount > 0

  return (
    <div className="billing-page" data-billing-layout="fp05">
      <header className="fp-header">
        <div className="fp-header__intro">
          <h2>{pageTitle}</h2>
          <p className="fp-header__lede">{pageLede}</p>
          <div className="fp-header__meta" aria-label="Métadonnées facturation">
            <span className="fp-chip fp-chip--source">ComptaPilot · Facturation</span>
            {typeof data.smtp_configured === 'boolean' ? (
              <span
                className={`fp-chip ${data.smtp_configured ? 'fp-chip--ok' : 'fp-chip--warn'}`}
              >
                {data.smtp_configured ? 'Envoi e-mail prêt' : 'Envoi e-mail à configurer'}
              </span>
            ) : null}
            <span className="fp-chip">
              {data.stats.documents} document{data.stats.documents === 1 ? '' : 's'}
            </span>
            {data.stats.unpaid > 0 ? (
              <span className="fp-chip fp-chip--warn">
                {data.stats.unpaid} impayé{data.stats.unpaid === 1 ? '' : 's'}
              </span>
            ) : null}
          </div>
          {fromLaunch ? (
            <p className="muted first-experience-back fp-header__back">
              <Link to="/dashboard">Retour au Dashboard</Link>
            </p>
          ) : null}
        </div>
        <div className="fp-header__actions">
          <button
            ref={createTriggerRef}
            type="button"
            className="btn"
            onClick={() => setCreateDialogOpen(true)}
          >
            Créer un document
          </button>
        </div>
      </header>

      <DocumentCreateFlow
        typeOpen={createDialogOpen}
        onTypeOpenChange={setCreateDialogOpen}
        customerId={prefillCustomerId}
        returnFocusRef={createTriggerRef}
        onDocumentsRefresh={(docId) => {
          load()
          if (docId != null) {
            /* highlight via ?doc= handled by existing openDocId effect */
          }
        }}
      />

      <section className="fp-section" aria-label="Indicateurs">
        <h3 className="fp-section__title">Essentiel</h3>
        <div className="fp-kpi-grid">
          <div className="fp-kpi">
            <span className="fp-kpi__label">Documents</span>
            <p className="fp-kpi__value">{data.stats.documents}</p>
          </div>
          <div className="fp-kpi">
            <span className="fp-kpi__label">Clients</span>
            <p className="fp-kpi__value">{data.stats.customers}</p>
          </div>
          <div className={`fp-kpi${unpaidEmphasis ? ' fp-kpi--alert' : ''}`}>
            <span className="fp-kpi__label">Impayés</span>
            <p className="fp-kpi__value">{data.stats.unpaid}</p>
          </div>
          <div className={`fp-kpi${unpaidEmphasis ? ' fp-kpi--emphasis' : ''}`}>
            <span className="fp-kpi__label">Montant dû</span>
            <p className="fp-kpi__value">{formatEuro(data.stats.unpaid_amount)}</p>
          </div>
        </div>
      </section>

      {prefillError ? (
        <div className="panel form-error" role="alert">
          {prefillError}
        </div>
      ) : null}

      {createdDoc && successPrimary ? (
        <FirstActionSuccessPanel
          title="Votre facture a été créée"
          description="Document enregistré en brouillon :"
          resourceName={createdDoc.number}
          primaryAction={successPrimary}
          secondaryActions={successSecondary}
        />
      ) : null}

      <section className="fp-section" aria-label={editingId ? 'Modification' : 'Répartition'}>
        {editingId ? <h3 className="fp-section__title">Modifier</h3> : null}
        <div className="billing-top">
        {editingId ? (
        <form className="panel billing-create" onSubmit={(e) => void onSubmit(e)}>
          <h3>{formTitle}</h3>
          <p className="muted first-experience-hint">
            La facture est enregistrée comme <strong>brouillon</strong>. Vous pourrez l’envoyer au
            client ensuite. Aucun e-mail n’est envoyé automatiquement.
          </p>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="bill_type">Type</label>
              <select
                id="bill_type"
                value={form.doc_type}
                disabled={Boolean(editingId) || submitting}
                onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
              >
                <option value="devis">Devis</option>
                <option value="facture">Facture</option>
                <option value="avoir">Avoir</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="bill_client">
                Client <span className="field-required">(obligatoire)</span>
              </label>
              <input
                id="bill_client"
                value={form.customer_name}
                onChange={(e) => fillFromCustomerName(e.target.value)}
                list="customers"
                required
                disabled={submitting}
              />
              <datalist id="customers">
                {data.customers.map((c) => (
                  <option key={c.id} value={c.name} />
                ))}
              </datalist>
              {form.customer_id ? (
                <p className="muted" style={{ margin: '0.35rem 0 0', fontSize: '0.85rem' }}>
                  Client sélectionné (id {form.customer_id}) — vous pouvez en choisir un autre.
                </p>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="bill_email">
                E-mail client <span className="muted">(facultatif)</span>
              </label>
              <input
                id="bill_email"
                type="email"
                value={form.customer_email}
                onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
                placeholder="optionnel"
                disabled={submitting}
              />
            </div>
            <div className="field">
              <label htmlFor="bill_tva">TVA %</label>
              <input
                id="bill_tva"
                type="number"
                step="0.1"
                value={form.vat_rate}
                onChange={(e) => setForm({ ...form, vat_rate: Number(e.target.value) })}
                disabled={submitting}
              />
            </div>
            <div className="field full">
              <label htmlFor="bill_notes">
                Notes <span className="muted">(facultatif)</span>
              </label>
              <input
                id="bill_notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                disabled={submitting}
              />
            </div>
            <SalesDocLinesEditor
              lines={lines}
              onChange={setLines}
              token={token}
              orgId={orgId}
              disabled={submitting}
            />
          </div>
          <div className="actions">
            <button className="btn" type="submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? 'Enregistrement…' : editingId ? 'Enregistrer' : 'Créer le brouillon'}
            </button>
            {editingId ? (
              <button
                className="btn secondary"
                type="button"
                onClick={resetForm}
                disabled={submitting}
              >
                Annuler
              </button>
            ) : null}
            {data.customers.length === 0 ? (
              <Link className="btn secondary" to={withLaunchSource('/clients')}>
                Ajouter un client d’abord
              </Link>
            ) : null}
          </div>
        </form>
        ) : null}

        <aside className="panel billing-pipeline">
          <h3>Répartition</h3>
          <div className="billing-pipeline-stats">
            <div>
              <span>Devis</span>
              <strong>{data.stats.quotes}</strong>
            </div>
            <div>
              <span>Factures</span>
              <strong>{data.stats.invoices}</strong>
            </div>
            <div>
              <span>Avoirs</span>
              <strong>{data.stats.credits}</strong>
            </div>
          </div>
          <p className="muted billing-pipeline-help">
            Devis → envoyer → signer → convertir · Facture → relancer → encaisser
          </p>
        </aside>
        </div>
      </section>

      {(message || error) && (
        <div className="billing-feedback">
          {message && <div className="auth-alert auth-alert-ok">{message}</div>}
          {error && <div className="auth-alert auth-alert-error">{error}</div>}
        </div>
      )}

      <section className="fp-section" aria-label="Documents">
        <h3 className="fp-section__title">Suivre</h3>
      <section className="panel billing-docs">
        <div className="billing-docs-head">
          <h3>Documents</h3>
          <div className="billing-tabs" role="tablist" aria-label="Filtrer par type">
            {(
              [
                ['all', 'Tous'],
                ['devis', 'Devis'],
                ['facture', 'Factures'],
                ['avoir', 'Avoirs'],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={typeFilter === value}
                className={`billing-tab${typeFilter === value ? ' active' : ''}`}
                onClick={() => setTypeFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {documents.length === 0 ? (
          typeFilter === 'facture' || (typeFilter === 'all' && data.documents.length === 0) ? (
            <EmptyState
              title="Aucune facture créée"
              description="Créez votre première facture et centralisez son suivi depuis ComptaPilot."
              action={
                data.customers.length === 0 ? (
                  <Link className="btn" to={withLaunchSource('/clients')}>
                    Ajouter un client
                  </Link>
                ) : (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setCreateDialogOpen(true)}
                  >
                    Créer un document
                  </button>
                )
              }
            />
          ) : (
            <div className="empty">Aucun document dans ce filtre.</div>
          )
        ) : (
          <div className="billing-table-wrap">
            <table className="billing-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Client</th>
                  <th>Date</th>
                  <th>Statut</th>
                  <th className="num">TTC</th>
                  <th className="num">Payé</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => {
                  const busy = busyId === doc.id
                  return (
                    <tr key={doc.id}>
                      <td>
                        <strong className="billing-doc-number">{doc.number}</strong>
                        <span className="billing-doc-type">
                          {TYPE_LABELS[doc.doc_type] || doc.doc_type}
                        </span>
                      </td>
                      <td>
                        <span className="billing-client">{doc.customer_name}</span>
                        {doc.customer_email ? (
                          <span className="muted billing-email">{doc.customer_email}</span>
                        ) : null}
                      </td>
                      <td>{doc.issue_date}</td>
                      <td>
                        <span className={statusBadgeClass(doc.status)}>
                          {STATUS_LABELS[doc.status] || doc.status}
                        </span>
                      </td>
                      <td className="num">{formatEuro(doc.amount_ttc)}</td>
                      <td className="num muted">{formatEuro(doc.paid_amount)}</td>
                      <td>
                        <div className="billing-row-actions">
                          <button
                            className="btn secondary btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => visualize(doc)}
                          >
                            Visualiser
                          </button>
                          <button
                            className="btn secondary btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => setPreviewDoc(doc)}
                          >
                            Envoyer
                          </button>
                          {doc.doc_type === 'devis' && (
                            <>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'sign')}
                              >
                                Signer
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'convert')}
                              >
                                → Facture
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void duplicate(doc)}
                              >
                                Dupliquer
                              </button>
                            </>
                          )}
                          {doc.doc_type === 'facture' && (
                            <>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy || doc.status === 'paid'}
                                onClick={() => setPayDoc(doc)}
                              >
                                Payer
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'remind')}
                              >
                                Relancer
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'credit-note')}
                              >
                                Avoir
                              </button>
                            </>
                          )}
                          <button
                            className="btn secondary btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => startEdit(doc)}
                          >
                            Modifier
                          </button>
                          <button
                            className="btn danger-outline btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => void remove(doc)}
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      </section>

      {previewDoc && token && orgId && (
        <SalesDocPreviewModal
          doc={previewDoc}
          token={token}
          orgId={orgId}
          onClose={() => setPreviewDoc(null)}
          onEdit={startEdit}
          onMarkPaid={(document) => {
            setPreviewDoc(null)
            setPayDoc(document)
          }}
          onRemind={(document) => {
            void act(document, 'remind')
          }}
          onSent={(document, log) => {
            setPreviewDoc(document)
            setMessage(
              log.status === 'sent' || log.status === 'mailto_opened'
                ? `E-mail traité pour ${log.recipient}`
                : `Envoi ${log.status} pour ${document.number}`,
            )
            load()
          }}
        />
      )}

      {payDoc && (
        <InvoicePaymentModal
          doc={payDoc}
          busy={busyId === payDoc.id}
          onClose={() => setPayDoc(null)}
          onSubmit={submitPayment}
        />
      )}
    </div>
  )
}
