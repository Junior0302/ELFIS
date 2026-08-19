import type { FormEvent } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import { Button, FormField, Input, Stack } from '../design-system'
import {
  COMPANY_NAME_MAX_LENGTH,
  ENTERPRISE_SETUP_INDUSTRY_PATH,
  ENTERPRISE_SETUP_PATH,
  canSubmitCompanyName,
  normalizeCompanyName,
  validateCompanyName,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'

/**
 * Étape company_name — /onboarding/entreprise/nom
 * E1.4: FormField + Input + Button + Stack
 */
export default function EnterpriseSetupCompanyNamePage() {
  const navigate = useNavigate()
  const { draft, setCompanyName, persistDraft } = useEnterpriseSetupDraft()
  const [value, setValue] = useState(draft.company_name)
  const [touched, setTouched] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()
  const errorId = `${inputId}-error`

  useEffect(() => {
    setValue(draft.company_name)
  }, [draft.company_name])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const error = touched ? validateCompanyName(value) : null
  const canContinue = canSubmitCompanyName(value) && !submitting

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    setTouched(true)
    if (!canSubmitCompanyName(value) || submitting) return
    const normalized = normalizeCompanyName(value)
    setSubmitting(true)
    setCompanyName(normalized)
    persistDraft({ ...draft, company_name: normalized })
    navigate(ENTERPRISE_SETUP_INDUSTRY_PATH)
  }

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={`${inputId}-title`}>
      <EnterpriseSetupProgress stepId="company_name" />
      <Stack gap={4}>
        <div>
          <h2 id={`${inputId}-title`}>Comment s’appelle votre entreprise ?</h2>
          <p className="enterprise-setup-lead">
            Indiquez le nom officiel ou commercial que vous souhaitez utiliser dans ComptaPilot.
          </p>
        </div>

        <form className="enterprise-setup-form" onSubmit={submit} noValidate>
          <Stack gap={5}>
            <FormField label="Nom de l’entreprise" htmlFor={inputId} error={error} required>
              <Input
                ref={inputRef}
                id={inputId}
                name="company_name"
                type="text"
                autoComplete="organization"
                placeholder="Ex. Dupont Services"
                maxLength={COMPANY_NAME_MAX_LENGTH}
                value={value}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? errorId : undefined}
                onChange={(e) => {
                  setValue(e.target.value)
                  setCompanyName(e.target.value)
                }}
                onBlur={() => setTouched(true)}
              />
            </FormField>

            <div className="enterprise-setup-actions">
              <Button type="submit" disabled={!canContinue}>
                Continuer
              </Button>
              <Link className="btn secondary" to={ENTERPRISE_SETUP_PATH}>
                Retour
              </Link>
            </div>
          </Stack>
        </form>
      </Stack>
    </section>
  )
}
