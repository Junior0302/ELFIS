import type { FormEvent } from 'react'
import { useEffect, useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import CountryCombobox from '../components/CountryCombobox'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import { normalizeCountryCode } from '../countries'
import {
  ENTERPRISE_SETUP_CURRENCY_PATH,
  ENTERPRISE_SETUP_INDUSTRY_PATH,
  canSubmitCountry,
  validateCountry,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'

/**
 * Étape country — /onboarding/entreprise/pays
 * Combobox unique (autocomplétion + clavier).
 */
export default function EnterpriseSetupCountryPage() {
  const navigate = useNavigate()
  const { draft, setCountry, persistDraft } = useEnterpriseSetupDraft()
  const [country, setCountryLocal] = useState(draft.country)
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const titleId = useId()
  const errorId = useId()
  const fieldId = useId()

  useEffect(() => {
    setCountryLocal(draft.country)
  }, [draft.country])

  const error = touched ? validateCountry(country) : null
  const canContinue = canSubmitCountry(country) && !submitting

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    setTouched(true)
    if (!canSubmitCountry(country) || submitting) return
    setSubmitting(true)
    const normalized = normalizeCountryCode(country)
    setCountry(normalized)
    persistDraft({ ...draft, country: normalized })
    navigate(ENTERPRISE_SETUP_CURRENCY_PATH)
  }

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={titleId}>
      <EnterpriseSetupProgress stepId="country" />
      <h2 id={titleId}>Dans quel pays votre entreprise est-elle établie ?</h2>
      <p className="enterprise-setup-lead">
        Nous utiliserons ce pays pour adapter les paramètres fiscaux et les documents de votre
        espace.
      </p>

      <form className="enterprise-setup-form" onSubmit={submit} noValidate>
        <div className="field full">
          <label htmlFor={fieldId}>Pays de l’entreprise</label>
          <CountryCombobox
            id={fieldId}
            value={country}
            describedBy={error ? errorId : undefined}
            onChange={(code) => {
              setCountryLocal(code)
              if (code) setCountry(code)
              setTouched(true)
            }}
            onBlur={() => setTouched(true)}
          />
        </div>

        {error ? (
          <p id={errorId} className="enterprise-setup-field-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="enterprise-setup-actions">
          <button className="btn" type="submit" disabled={!canContinue}>
            Continuer
          </button>
          <Link className="btn secondary" to={ENTERPRISE_SETUP_INDUSTRY_PATH}>
            Retour
          </Link>
        </div>
      </form>
    </section>
  )
}
