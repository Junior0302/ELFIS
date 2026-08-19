import type { FormEvent, KeyboardEvent } from 'react'
import { useEffect, useId, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import { getCountryLabel } from '../countries'
import {
  filterCurrencies,
  formatCurrencyOption,
  getCurrencyByCode,
  normalizeCurrencyCode,
  recommendedCurrencyForCountry,
} from '../currencies'
import {
  ENTERPRISE_SETUP_COUNTRY_PATH,
  ENTERPRISE_SETUP_VAT_PATH,
  canSubmitCurrency,
  validateCurrency,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'

/**
 * Étape currency — /onboarding/entreprise/devise
 */
export default function EnterpriseSetupCurrencyPage() {
  const navigate = useNavigate()
  const { draft, setCurrency, persistDraft } = useEnterpriseSetupDraft()
  const recommended = useMemo(
    () => recommendedCurrencyForCountry(draft.country),
    [draft.country],
  )
  const recommendedCurrency = recommended ? getCurrencyByCode(recommended) : undefined
  const countryLabel = getCountryLabel(draft.country)

  const [currency, setCurrencyLocal] = useState(() => {
    if (draft.currency) return draft.currency
    return recommended || ''
  })
  const [query, setQuery] = useState('')
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const titleId = useId()
  const errorId = useId()
  const searchId = useId()
  const listLabelId = useId()

  const filtered = useMemo(() => filterCurrencies(query), [query])

  useEffect(() => {
    if (draft.currency) {
      setCurrencyLocal(draft.currency)
      return
    }
    if (recommended) {
      setCurrencyLocal(recommended)
    }
  }, [draft.currency, recommended])

  const error = touched ? validateCurrency(currency) : null
  const canContinue = canSubmitCurrency(currency) && !submitting

  const selectCurrency = (code: string) => {
    const normalized = normalizeCurrencyCode(code)
    setCurrencyLocal(normalized)
    setCurrency(normalized)
    setTouched(true)
  }

  const onCardKeyDown = (event: KeyboardEvent<HTMLButtonElement>, code: string) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      selectCurrency(code)
    }
  }

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    setTouched(true)
    if (!canSubmitCurrency(currency) || submitting) return
    setSubmitting(true)
    const normalized = normalizeCurrencyCode(currency)
    setCurrency(normalized)
    persistDraft({ ...draft, currency: normalized })
    navigate(ENTERPRISE_SETUP_VAT_PATH)
  }

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={titleId}>
      <EnterpriseSetupProgress stepId="currency" />
      <h2 id={titleId}>Quelle est la devise principale de votre entreprise ?</h2>
      <p className="enterprise-setup-lead">
        Nous utiliserons cette devise par défaut pour vos documents et vos tableaux de bord.
      </p>

      <form className="enterprise-setup-form" onSubmit={submit} noValidate>
        {recommendedCurrency ? (
          <div className="enterprise-setup-currency-recommended">
            <p className="enterprise-setup-kicker">Devise recommandée</p>
            <button
              type="button"
              className={`enterprise-setup-industry-card enterprise-setup-currency-card${
                currency === recommendedCurrency.code ? ' is-selected' : ''
              }`}
              aria-pressed={currency === recommendedCurrency.code}
              aria-selected={currency === recommendedCurrency.code}
              onClick={() => selectCurrency(recommendedCurrency.code)}
              onKeyDown={(event) => onCardKeyDown(event, recommendedCurrency.code)}
            >
              <span className="enterprise-setup-currency-check" aria-hidden>
                ✓
              </span>
              <span>
                <strong>{formatCurrencyOption(recommendedCurrency)}</strong>
                {countryLabel ? (
                  <em className="enterprise-setup-currency-hint">
                    Recommandée pour {countryLabel === 'France' ? 'la France' : countryLabel}
                  </em>
                ) : null}
              </span>
            </button>
          </div>
        ) : null}

        <div className="enterprise-setup-currency-all">
          <p id={listLabelId} className="enterprise-setup-kicker">
            Toutes les devises
          </p>
          <div className="field full">
            <label htmlFor={searchId}>Rechercher une devise</label>
            <input
              id={searchId}
              type="search"
              value={query}
              placeholder="Ex. EUR, €, dollar…"
              autoComplete="off"
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          {filtered.length === 0 ? (
            <p className="enterprise-setup-field-error" role="status">
              Aucune devise ne correspond à votre recherche.
            </p>
          ) : (
            <div
              className="enterprise-setup-industry-grid"
              role="listbox"
              aria-labelledby={listLabelId}
              aria-activedescendant={
                currency ? `currency-option-${currency}` : undefined
              }
            >
              {filtered.map((option) => {
                const selected = currency === option.code
                return (
                  <button
                    key={option.code}
                    id={`currency-option-${option.code}`}
                    type="button"
                    role="option"
                    className={`enterprise-setup-industry-card${selected ? ' is-selected' : ''}`}
                    aria-selected={selected}
                    onClick={() => selectCurrency(option.code)}
                    onKeyDown={(event) => onCardKeyDown(event, option.code)}
                  >
                    {formatCurrencyOption(option)}
                    <span className="enterprise-setup-currency-symbol muted">{option.symbol}</span>
                  </button>
                )
              })}
            </div>
          )}
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
          <Link className="btn secondary" to={ENTERPRISE_SETUP_COUNTRY_PATH}>
            Retour
          </Link>
        </div>
      </form>
    </section>
  )
}
