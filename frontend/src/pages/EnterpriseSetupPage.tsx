import { Link } from 'react-router-dom'
import { ENTERPRISE_SETUP_START_PATH } from '../enterpriseSetup'

/**
 * Introduction Enterprise Setup — /onboarding/entreprise
 */
export default function EnterpriseSetupPage() {
  return (
    <section className="panel enterprise-setup-page" aria-label="Préparation entreprise">
      <p className="enterprise-setup-kicker">Configuration</p>
      <h2>Préparons votre entreprise</h2>
      <p className="enterprise-setup-lead">
        Avant de commencer à utiliser ComptaPilot, nous allons configurer votre espace de
        travail.
      </p>
      <p className="muted enterprise-setup-note">
        Cette configuration prendra seulement quelques minutes.
      </p>
      <div className="enterprise-setup-actions">
        <Link className="btn" to={ENTERPRISE_SETUP_START_PATH}>
          Commencer la configuration
        </Link>
      </div>
    </section>
  )
}
