import { useEffect, useId, useMemo } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import EnterpriseSetupProgress from '../components/EnterpriseSetupProgress'
import { getCountryLabel } from '../countries'
import { formatCurrencyOption, getCurrencyByCode } from '../currencies'
import {
  ENTERPRISE_SETUP_COMPANY_NAME_PATH,
  ENTERPRISE_SETUP_COUNTRY_PATH,
  ENTERPRISE_SETUP_CURRENCY_PATH,
  ENTERPRISE_SETUP_INDUSTRY_PATH,
  ENTERPRISE_SETUP_PREPARATION_PATH,
  ENTERPRISE_SETUP_VAT_PATH,
  firstIncompleteEnterpriseSetupPath,
  getIndustryLabel,
  getVatSummaryLabel,
  isEnterpriseSetupDraftComplete,
} from '../enterpriseSetup'
import { useEnterpriseSetupDraft } from '../enterpriseSetupContext'

type SummaryRow = {
  id: string
  label: string
  value: string
  editPath: string
}

/**
 * Étape 6 — résumé de configuration.
 */
export default function EnterpriseSetupSummaryPage() {
  const navigate = useNavigate()
  const { draft } = useEnterpriseSetupDraft()
  const titleId = useId()

  const incompletePath = firstIncompleteEnterpriseSetupPath(draft)

  useEffect(() => {
    if (incompletePath) {
      navigate(incompletePath, { replace: true })
    }
  }, [incompletePath, navigate])

  const rows = useMemo<SummaryRow[]>(() => {
    const currency = getCurrencyByCode(draft.currency)
    const industryLabel = getIndustryLabel(draft.industry, draft.industry_other ?? '')
    const items: SummaryRow[] = [
      {
        id: 'company_name',
        label: 'Nom de l’entreprise',
        value: draft.company_name,
        editPath: ENTERPRISE_SETUP_COMPANY_NAME_PATH,
      },
      {
        id: 'industry',
        label: 'Secteur d’activité',
        value: industryLabel,
        editPath: ENTERPRISE_SETUP_INDUSTRY_PATH,
      },
      {
        id: 'country',
        label: 'Pays',
        value: getCountryLabel(draft.country),
        editPath: ENTERPRISE_SETUP_COUNTRY_PATH,
      },
      {
        id: 'currency',
        label: 'Devise principale',
        value: currency ? formatCurrencyOption(currency) : '',
        editPath: ENTERPRISE_SETUP_CURRENCY_PATH,
      },
      {
        id: 'vat',
        label: 'TVA',
        value: getVatSummaryLabel(draft.vat_status),
        editPath: ENTERPRISE_SETUP_VAT_PATH,
      },
    ]
    if (draft.vat_status === 'vat_registered' && draft.vat_number) {
      items.push({
        id: 'vat_number',
        label: 'Numéro de TVA',
        value: draft.vat_number,
        editPath: ENTERPRISE_SETUP_VAT_PATH,
      })
    }
    return items
  }, [draft])

  if (incompletePath) {
    return <Navigate to={incompletePath} replace />
  }

  const canCreate = isEnterpriseSetupDraftComplete(draft)

  return (
    <section className="panel enterprise-setup-page" aria-labelledby={titleId}>
      <EnterpriseSetupProgress stepId="summary" />
      <h2 id={titleId}>Vérifiez les informations de votre entreprise</h2>
      <p className="enterprise-setup-lead">
        Vous pourrez encore modifier ces informations avant de créer votre espace.
      </p>

      <ul className="enterprise-setup-summary-list">
        {rows.map((row) => (
          <li key={row.id} className="enterprise-setup-summary-row">
            <div className="enterprise-setup-summary-copy">
              <p className="enterprise-setup-summary-label">{row.label}</p>
              <p className="enterprise-setup-summary-value">{row.value}</p>
            </div>
            <Link className="linkish enterprise-setup-summary-edit" to={row.editPath}>
              Modifier
            </Link>
          </li>
        ))}
      </ul>

      <div className="enterprise-setup-actions">
        <button
          className="btn"
          type="button"
          disabled={!canCreate}
          onClick={() => navigate(ENTERPRISE_SETUP_PREPARATION_PATH)}
        >
          Créer mon espace
        </button>
        <Link className="btn secondary" to={ENTERPRISE_SETUP_VAT_PATH}>
          Retour
        </Link>
      </div>
    </section>
  )
}
