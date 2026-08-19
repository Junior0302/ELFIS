import { Navigate } from 'react-router-dom'
import { ENTERPRISE_SETUP_SUMMARY_PATH } from '../enterpriseSetup'

/** Ancienne étape banque → résumé (C1.10). */
export default function EnterpriseSetupBankPlaceholderPage() {
  return <Navigate to={ENTERPRISE_SETUP_SUMMARY_PATH} replace />
}
