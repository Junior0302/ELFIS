import type { FormEvent, KeyboardEvent } from 'react'
import { useEffect, useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import {
  ENTERPRISE_SETUP_CURRENCY_PATH,
  ENTERPRISE_SETUP_SUMMARY_PATH,
  ENTERPRISE_SETUP_VAT_STATUSES,
  VAT_NUMBER_MAX_LENGTH,
  canSubmitVatStatus,
  normalizeVatNumber,
  validateVatNumber,
  validateVatStatus,
  vatHelpTextForCountry,
  type EnterpriseSetupVatStatus,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'

/**
 * Étape vat — /onboarding/entreprise/tva
 */
export default function EnterpriseSetupVatPage() {
  const navigate = useNavigate()
  const { draft, setVatStatus, persistDraft } = useEnterpriseSetupDraft()
  const [status, setStatusLocal] = useState(draft.vat_status)
  const [vatNumber, setVatNumberLocal] = useState(draft.vat_number ?? '')
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const titleId = useId()
  const helpId = useId()
  const errorId = useId()
  const numberId = useId()
  const numberHintId = useId()
  const groupLabelId = useId()

  useEffect(() => {
    setStatusLocal(draft.vat_status)
    setVatNumberLocal(draft.vat_number ?? '')
  }, [draft.vat_status, draft.vat_number])

  const help = vatHelpTextForCountry(draft.country)
  const statusError = touched ? validateVatStatus(status, vatNumber) : null
  const numberError =
    touched && status === 'vat_registered' ? validateVatNumber(vatNumber) : null
  const error = statusError || numberError
  const canContinue = canSubmitVatStatus(status, vatNumber) && !submitting

  const selectStatus = (next: EnterpriseSetupVatStatus) => {
    setStatusLocal(next)
    if (next === 'vat_registered') {
      setVatStatus(next, vatNumber)
    } else {
      setVatNumberLocal('')
      setVatStatus(next)
    }
  }

  const onCardKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    next: EnterpriseSetupVatStatus,
  ) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      selectStatus(next)
    }
  }

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    setTouched(true)
    if (!canSubmitVatStatus(status, vatNumber) || submitting) return
    setSubmitting(true)
    const normalizedNumber = normalizeVatNumber(vatNumber)
    const next =
      status === 'vat_registered'
        ? {
            ...draft,
            vat_status: status,
            ...(normalizedNumber ? { vat_number: normalizedNumber } : {}),
          }
        : {
            ...draft,
            vat_status: status,
            vat_number: undefined,
          }
    if (status !== 'vat_registered') {
      delete next.vat_number
    }
    setVatStatus(status as EnterpriseSetupVatStatus, normalizedNumber)
    persistDraft(next)
    navigate(ENTERPRISE_SETUP_SUMMARY_PATH)
  }

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={titleId}>
      <EnterpriseSetupProgress stepId="vat" />
      <h2 id={titleId}>Votre entreprise facture-t-elle la TVA ?</h2>
      <p className="enterprise-setup-lead">
        Cette information nous permettra d’adapter vos documents et vos paramètres comptables.
      </p>
      <p id={helpId} className="enterprise-setup-vat-help muted">
        {help}
      </p>

      <form className="enterprise-setup-form" onSubmit={submit} noValidate>
        <div
          className="enterprise-setup-vat-options"
          role="radiogroup"
          aria-labelledby={groupLabelId}
          aria-describedby={helpId}
        >
          <p id={groupLabelId} className="visually-hidden">
            Statut de TVA
          </p>
          {ENTERPRISE_SETUP_VAT_STATUSES.map((option) => {
            const selected = status === option.id
            return (
              <button
                key={option.id}
                type="button"
                role="radio"
                className={`enterprise-setup-industry-card enterprise-setup-vat-card${
                  selected ? ' is-selected' : ''
                }`}
                aria-checked={selected}
                aria-pressed={selected}
                onClick={() => selectStatus(option.id)}
                onKeyDown={(event) => onCardKeyDown(event, option.id)}
              >
                <strong>{option.label}</strong>
                <span className="enterprise-setup-vat-card-desc">{option.description}</span>
              </button>
            )
          })}
        </div>

        {status === 'vat_registered' ? (
          <div className="field full">
            <label htmlFor={numberId}>Numéro de TVA intracommunautaire</label>
            <input
              id={numberId}
              name="vat_number"
              type="text"
              inputMode="text"
              autoComplete="off"
              placeholder="Ex. FR12345678901"
              maxLength={VAT_NUMBER_MAX_LENGTH}
              value={vatNumber}
              aria-invalid={Boolean(numberError)}
              aria-describedby={`${numberHintId}${numberError ? ` ${errorId}` : ''}`}
              onChange={(e) => {
                const next = e.target.value
                setVatNumberLocal(next)
                setVatStatus('vat_registered', next)
              }}
              onBlur={() => setTouched(true)}
            />
            <p id={numberHintId} className="field-hint muted">
              Facultatif — vous pourrez également l’ajouter plus tard.
            </p>
          </div>
        ) : null}

        {error ? (
          <p id={errorId} className="enterprise-setup-field-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="enterprise-setup-actions">
          <button className="btn" type="submit" disabled={!canContinue}>
            Continuer
          </button>
          <Link className="btn secondary" to={ENTERPRISE_SETUP_CURRENCY_PATH}>
            Retour
          </Link>
        </div>
      </form>
    </section>
  )
}
