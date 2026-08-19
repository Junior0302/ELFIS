/**
 * Proposal → Invoice conversion panel (S1.6.1).
 * All amounts come from the backend — no frontend calculation.
 */
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Badge, Button, EmptyState, FormField, Input, Section, Stack } from '../design-system'
import { ConfirmDialog } from '../design-system/overlays'
import { formatSalesMoney } from './salesDashboard'
import type {
  CustomerResolutionMode,
  ConvertToInvoiceResult,
  InvoiceConversionPreview,
  ProposalConversionState,
} from './salesProposals'
import { invoiceFromProposalPath } from './salesProposals'

type Props = {
  token: string
  orgId: number
  proposalId: number
  proposalUpdatedAt?: string | null
  onConverted?: () => void
}

type Candidate = {
  customer_id?: number
  id?: number
  name?: string
  email?: string
  phone?: string
  match_level?: string
  match_reasons?: string[]
  can_select?: boolean
  record?: { id?: number; name?: string; email?: string }
}

function candidateId(c: Candidate): number | null {
  const id = c.customer_id ?? c.id ?? c.record?.id
  return typeof id === 'number' ? id : null
}

function candidateName(c: Candidate): string {
  return c.name || c.record?.name || `Client #${candidateId(c) ?? '?'}`
}

export function ProposalConversionPanel({
  token,
  orgId,
  proposalId,
  proposalUpdatedAt,
  onConverted,
}: Props) {
  const titleId = useId()
  const [state, setState] = useState<ProposalConversionState | null>(null)
  const [preview, setPreview] = useState<InvoiceConversionPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [result, setResult] = useState<ConvertToInvoiceResult | null>(null)
  const [mode, setMode] = useState<CustomerResolutionMode>('use_linked_customer')
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null)
  const [confirmPossible, setConfirmPossible] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createPhone, setCreatePhone] = useState('')
  const [createAddress, setCreateAddress] = useState('')
  const [createVat, setCreateVat] = useState('')
  const convertingLock = useRef(false)

  const loadState = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const next = await api.getSalesProposalConversionState(token, orgId, proposalId)
      setState(next)
      if (next.linked_customer_id) {
        setMode('use_linked_customer')
        setSelectedCustomerId(next.linked_customer_id)
      } else if ((next.duplicate_candidates?.exact_match || []).length > 0) {
        setMode('use_existing_customer')
      } else {
        setMode('create_new_customer')
      }
      if (next.linked_invoice_id) {
        setResult({
          already_converted: true,
          proposal_id: next.proposal_id,
          invoice_id: next.linked_invoice_id,
          invoice_number: '',
          invoice_status: 'draft',
          customer_id: next.linked_customer_id,
          message: 'Cette proposition a déjà été convertie',
        })
      }
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'État de conversion indisponible',
      )
    } finally {
      setLoading(false)
    }
  }, [token, orgId, proposalId])

  useEffect(() => {
    void loadState()
  }, [loadState])

  const refreshPreview = async (customerId?: number | null) => {
    setBusy(true)
    setError('')
    try {
      const next = await api.getSalesProposalConversionPreview(
        token,
        orgId,
        proposalId,
        customerId ?? selectedCustomerId,
      )
      setPreview(next)
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Aperçu indisponible',
      )
    } finally {
      setBusy(false)
    }
  }

  const resolveCustomer = async () => {
    setBusy(true)
    setError('')
    try {
      const body =
        mode === 'create_new_customer'
          ? {
              customer_resolution_mode: mode,
              customer_payload: {
                name: createName,
                email: createEmail,
                phone: createPhone,
                address: createAddress,
                vat_number: createVat,
              },
              confirm_possible_match: confirmPossible,
            }
          : {
              customer_resolution_mode: mode,
              customer_id: mode === 'use_linked_customer' ? state?.linked_customer_id : selectedCustomerId,
              confirm_possible_match: confirmPossible,
            }
      const resolved = await api.resolveSalesProposalConversionCustomer(
        token,
        orgId,
        proposalId,
        body,
      )
      setSelectedCustomerId(resolved.customer.id)
      setMode('use_linked_customer')
      await loadState()
      await refreshPreview(resolved.customer.id)
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Résolution client échouée',
      )
    } finally {
      setBusy(false)
    }
  }

  const runConvert = async () => {
    if (convertingLock.current || busy) return
    convertingLock.current = true
    setBusy(true)
    setError('')
    try {
      const idempotencyKey =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `convert-${proposalId}-${Date.now()}`
      const converted = await api.convertSalesProposalToInvoice(token, orgId, proposalId, {
        customer_resolution_mode: mode,
        customer_id:
          mode === 'use_linked_customer'
            ? state?.linked_customer_id ?? selectedCustomerId
            : selectedCustomerId,
        customer_payload:
          mode === 'create_new_customer'
            ? {
                name: createName,
                email: createEmail,
                phone: createPhone,
                address: createAddress,
                vat_number: createVat,
              }
            : undefined,
        accepted_version_id: state?.accepted_version_id,
        expected_proposal_updated_at: proposalUpdatedAt,
        idempotency_key: idempotencyKey,
        confirm_possible_match: confirmPossible,
      })
      setResult(converted)
      await loadState()
      onConverted?.()
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Conversion échouée'
      setError(msg)
      throw err
    } finally {
      setBusy(false)
      convertingLock.current = false
    }
  }

  if (loading) {
    return (
      <Section title="Conversion ComptaPilot" spacing="compact">
        <p className="muted">Chargement de l’état de conversion…</p>
      </Section>
    )
  }

  if (!state) {
    return (
      <Section title="Conversion ComptaPilot" spacing="compact">
        <EmptyState title="Conversion indisponible" description={error || undefined} />
      </Section>
    )
  }

  const exact = (state.duplicate_candidates?.exact_match || []) as Candidate[]
  const possible = (state.duplicate_candidates?.possible_match || []) as Candidate[]
  const converted = state.conversion_status === 'converted' || Boolean(state.linked_invoice_id)

  return (
    <Section title="Conversion ComptaPilot" spacing="compact" aria-labelledby={titleId}>
      <h3 id={titleId} className="sr-only">
        Conversion proposition vers facture
      </h3>
      <Stack gap={4}>
        <div className="sales-workspace__header-meta">
          <Badge tone={converted ? 'ok' : 'accent'}>{state.conversion_status}</Badge>
          <Badge tone="neutral">{state.proposal_status}</Badge>
        </div>

        {error ? <p className="muted sales-workspace__banner" role="alert">{error}</p> : null}

        {(state.blockers || []).length > 0 ? (
          <ul className="sales-workspace__list">
            {state.blockers!.map((b) => (
              <li key={b} className="sales-workspace__list-item">
                <strong>Blocage</strong>
                <p className="muted">{b}</p>
              </li>
            ))}
          </ul>
        ) : null}

        {(state.warnings || []).length > 0 ? (
          <ul className="sales-workspace__list">
            {state.warnings!.map((w) => (
              <li key={w} className="sales-workspace__list-item">
                <strong>Avertissement</strong>
                <p className="muted">{w}</p>
              </li>
            ))}
          </ul>
        ) : null}

        {converted && (result || state.linked_invoice_id) ? (
          <div className="sales-workspace__list-item">
            <header>
              <strong>
                {result?.message || 'Cette proposition a déjà été convertie'}
              </strong>
            </header>
            <p className="muted">
              Facture {result?.invoice_number || `#${state.linked_invoice_id}`} · statut{' '}
              {result?.invoice_status || 'draft'}
            </p>
            <Link
              to={invoiceFromProposalPath(result?.invoice_id || state.linked_invoice_id!)}
              className="ds-btn btn primary"
            >
              Ouvrir la facture dans ComptaPilot
            </Link>
          </div>
        ) : (
          <>
            <Section title="Résolution client" spacing="compact">
              <Stack gap={3}>
                <label className="sales-workspace__meta-row">
                  <input
                    type="radio"
                    name="customer-mode"
                    checked={mode === 'use_linked_customer'}
                    disabled={!state.linked_customer_id}
                    onChange={() => setMode('use_linked_customer')}
                  />
                  Client déjà lié
                  {state.linked_customer_id ? ` (#${state.linked_customer_id})` : ' — aucun'}
                </label>
                <label className="sales-workspace__meta-row">
                  <input
                    type="radio"
                    name="customer-mode"
                    checked={mode === 'use_existing_customer'}
                    onChange={() => setMode('use_existing_customer')}
                  />
                  Sélectionner un client existant
                </label>
                <label className="sales-workspace__meta-row">
                  <input
                    type="radio"
                    name="customer-mode"
                    checked={mode === 'create_new_customer'}
                    onChange={() => setMode('create_new_customer')}
                  />
                  Créer un nouveau client
                </label>

                {exact.length > 0 ? (
                  <div>
                    <p>
                      <strong>Correspondances exactes</strong>
                    </p>
                    <ul className="sales-workspace__list">
                      {exact.map((c) => {
                        const id = candidateId(c)
                        return (
                          <li key={String(id)} className="sales-workspace__list-item">
                            <header>
                              <strong>{candidateName(c)}</strong>
                              <Badge tone="ok">exact</Badge>
                            </header>
                            <p className="muted">{c.email || c.record?.email || '—'}</p>
                            {id != null ? (
                              <Button
                                type="button"
                                size="sm"
                                variant="secondary"
                                disabled={busy}
                                onClick={() => {
                                  setMode('use_existing_customer')
                                  setSelectedCustomerId(id)
                                  setConfirmPossible(false)
                                }}
                              >
                                Sélectionner
                              </Button>
                            ) : null}
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                ) : null}

                {possible.length > 0 ? (
                  <div>
                    <p>
                      <strong>Correspondances possibles</strong>
                    </p>
                    <ul className="sales-workspace__list">
                      {possible.map((c) => {
                        const id = candidateId(c)
                        return (
                          <li key={String(id)} className="sales-workspace__list-item">
                            <header>
                              <strong>{candidateName(c)}</strong>
                              <Badge tone="warn">possible</Badge>
                            </header>
                            <p className="muted">
                              {(c.match_reasons || []).join(', ') || c.email || '—'}
                            </p>
                            {id != null ? (
                              <Button
                                type="button"
                                size="sm"
                                variant="secondary"
                                disabled={busy}
                                onClick={() => {
                                  setMode('use_existing_customer')
                                  setSelectedCustomerId(id)
                                  setConfirmPossible(true)
                                }}
                              >
                                Sélectionner (confirmation requise)
                              </Button>
                            ) : null}
                          </li>
                        )
                      })}
                    </ul>
                    {confirmPossible ? (
                      <label className="sales-workspace__meta-row">
                        <input
                          type="checkbox"
                          checked={confirmPossible}
                          onChange={(e) => setConfirmPossible(e.target.checked)}
                        />
                        Je confirme la sélection d’une correspondance possible (aucune fusion)
                      </label>
                    ) : null}
                  </div>
                ) : null}

                {mode === 'create_new_customer' ? (
                  <Stack gap={2}>
                    <FormField label="Nom" htmlFor="conv-customer-name">
                      <Input
                        id="conv-customer-name"
                        value={createName}
                        onChange={(e) => setCreateName(e.target.value)}
                        autoComplete="organization"
                      />
                    </FormField>
                    <FormField label="Email" htmlFor="conv-customer-email">
                      <Input
                        id="conv-customer-email"
                        type="email"
                        value={createEmail}
                        onChange={(e) => setCreateEmail(e.target.value)}
                      />
                    </FormField>
                    <FormField label="Téléphone" htmlFor="conv-customer-phone">
                      <Input
                        id="conv-customer-phone"
                        value={createPhone}
                        onChange={(e) => setCreatePhone(e.target.value)}
                      />
                    </FormField>
                    <FormField label="Adresse" htmlFor="conv-customer-address">
                      <Input
                        id="conv-customer-address"
                        value={createAddress}
                        onChange={(e) => setCreateAddress(e.target.value)}
                      />
                    </FormField>
                    <FormField label="TVA / identifiant" htmlFor="conv-customer-vat">
                      <Input
                        id="conv-customer-vat"
                        value={createVat}
                        onChange={(e) => setCreateVat(e.target.value)}
                      />
                    </FormField>
                  </Stack>
                ) : null}

                <div className="sales-deal__header-actions">
                  <Button type="button" variant="secondary" disabled={busy} onClick={() => void resolveCustomer()}>
                    Valider le client
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void refreshPreview()}
                  >
                    Actualiser l’aperçu
                  </Button>
                </div>
              </Stack>
            </Section>

            <Section title="Aperçu facture brouillon" spacing="compact">
              {!preview ? (
                <EmptyState
                  title="Aucun aperçu"
                  description="Résolvez le client puis actualisez l’aperçu. Aucun calcul côté navigateur."
                />
              ) : (
                <Stack gap={3}>
                  {(preview.blockers || []).map((b) => (
                    <p key={b} className="muted" role="status">
                      Blocage : {b}
                    </p>
                  ))}
                  <dl className="sales-workspace__meta-row">
                    <div>
                      <dt>Client</dt>
                      <dd>{preview.customer?.name || '—'}</dd>
                    </div>
                    <div>
                      <dt>Lignes</dt>
                      <dd>{preview.invoice_lines.length}</dd>
                    </div>
                    <div>
                      <dt>Sous-total</dt>
                      <dd>{formatSalesMoney(preview.subtotal)}</dd>
                    </div>
                    <div>
                      <dt>Taxes</dt>
                      <dd>{formatSalesMoney(preview.tax_total)}</dd>
                    </div>
                    <div>
                      <dt>Total</dt>
                      <dd>{formatSalesMoney(preview.total)} {preview.currency}</dd>
                    </div>
                    <div>
                      <dt>Statut cible</dt>
                      <dd>draft</dd>
                    </div>
                  </dl>
                  <p className="muted">
                    La facture sera créée en brouillon et ne sera pas envoyée automatiquement.
                  </p>
                  <Button
                    type="button"
                    variant="primary"
                    disabled={busy || !preview.can_confirm}
                    onClick={() => setConfirmOpen(true)}
                  >
                    Créer la facture brouillon
                  </Button>
                </Stack>
              )}
            </Section>
          </>
        )}
      </Stack>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Confirmer la conversion"
        description="Créer une facture brouillon ComptaPilot depuis la version acceptée. Aucun envoi automatique."
        confirmLabel="Créer la facture brouillon"
        tone="warning"
        loading={busy}
        confirmDisabled={busy || convertingLock.current}
        error={error || null}
        details={
          preview ? (
            <ul>
              <li>Proposition : {preview.proposal.proposal_number}</li>
              <li>Version : V{preview.accepted_version.version_number}</li>
              <li>Client : {preview.customer?.name || '—'}</li>
              <li>Lignes : {preview.invoice_lines.length}</li>
              <li>
                Total : {formatSalesMoney(preview.total)} {preview.currency}
              </li>
              <li>Conditions : {preview.payment_terms || '—'}</li>
            </ul>
          ) : null
        }
        onConfirm={runConvert}
      />
    </Section>
  )
}
