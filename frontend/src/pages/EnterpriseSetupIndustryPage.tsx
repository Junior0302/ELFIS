import type { FormEvent, KeyboardEvent } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import {
  ENTERPRISE_SETUP_COMPANY_NAME_PATH,
  ENTERPRISE_SETUP_COUNTRY_PATH,
  ENTERPRISE_SETUP_INDUSTRIES,
  INDUSTRY_OTHER_MAX_LENGTH,
  canSubmitIndustry,
  normalizeIndustryOther,
  validateIndustrySelection,
  type EnterpriseSetupIndustryId,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'

/**
 * Étape industry — /onboarding/entreprise/secteur
 */
export default function EnterpriseSetupIndustryPage() {
  const navigate = useNavigate()
  const { draft, setIndustry, persistDraft } = useEnterpriseSetupDraft()
  const [industry, setIndustryLocal] = useState<string>(draft.industry)
  const [other, setOther] = useState(draft.industry_other ?? '')
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const otherRef = useRef<HTMLInputElement>(null)
  const titleId = useId()
  const errorId = useId()
  const otherId = useId()
  const groupLabelId = useId()

  useEffect(() => {
    setIndustryLocal(draft.industry)
    setOther(draft.industry_other ?? '')
  }, [draft.industry, draft.industry_other])

  useEffect(() => {
    if (industry === 'other') {
      otherRef.current?.focus()
    }
  }, [industry])

  const error = touched ? validateIndustrySelection(industry, other) : null
  const canContinue = canSubmitIndustry(industry, other) && !submitting

  const selectIndustry = (id: EnterpriseSetupIndustryId) => {
    setIndustryLocal(id)
    if (id === 'other') {
      setIndustry(id, other)
    } else {
      setOther('')
      setIndustry(id)
    }
  }

  const onCardKeyDown = (event: KeyboardEvent<HTMLButtonElement>, id: EnterpriseSetupIndustryId) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      selectIndustry(id)
    }
  }

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    setTouched(true)
    if (!canSubmitIndustry(industry, other) || submitting) return
    setSubmitting(true)
    const normalizedOther = normalizeIndustryOther(other)
    const next =
      industry === 'other'
        ? {
            ...draft,
            industry: 'other' as const,
            industry_other: normalizedOther,
          }
        : {
            ...draft,
            industry,
            industry_other: undefined,
          }
    if (industry !== 'other') {
      delete next.industry_other
    }
    setIndustry(
      industry as EnterpriseSetupIndustryId,
      industry === 'other' ? normalizedOther : undefined,
    )
    persistDraft(next)
    navigate(ENTERPRISE_SETUP_COUNTRY_PATH)
  }

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={titleId}>
      <EnterpriseSetupProgress stepId="industry" />
      <h2 id={titleId}>Dans quel secteur exerce votre entreprise ?</h2>
      <p className="enterprise-setup-lead">
        Cela nous permettra d’adapter les catégories, les recommandations et l’expérience à votre
        activité.
      </p>

      <form className="enterprise-setup-form" onSubmit={submit} noValidate>
        <div
          className="enterprise-setup-industry-grid"
          role="group"
          aria-labelledby={groupLabelId}
        >
          <p id={groupLabelId} className="visually-hidden">
            Secteur d’activité
          </p>
          {ENTERPRISE_SETUP_INDUSTRIES.map((option) => {
            const selected = industry === option.id
            return (
              <button
                key={option.id}
                type="button"
                className={`enterprise-setup-industry-card${selected ? ' is-selected' : ''}`}
                aria-pressed={selected}
                onClick={() => selectIndustry(option.id)}
                onKeyDown={(event) => onCardKeyDown(event, option.id)}
              >
                {option.label}
              </button>
            )
          })}
        </div>

        {industry === 'other' ? (
          <div className="field full">
            <label htmlFor={otherId}>Précisez votre secteur</label>
            <input
              ref={otherRef}
              id={otherId}
              name="industry_other"
              type="text"
              placeholder="Ex. Événementiel"
              maxLength={INDUSTRY_OTHER_MAX_LENGTH}
              value={other}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? errorId : undefined}
              onChange={(e) => {
                const next = e.target.value
                setOther(next)
                setIndustry('other', next)
              }}
              onBlur={() => setTouched(true)}
            />
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
          <Link className="btn secondary" to={ENTERPRISE_SETUP_COMPANY_NAME_PATH}>
            Retour
          </Link>
        </div>
      </form>
    </section>
  )
}
