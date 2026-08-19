import { Link } from 'react-router-dom'
import '../../platform-workspace/platform-workspace.css'

/**
 * Paramètres e-mail infrastructure — ELFIS Core.
 * Les modèles métier facture restent dans ComptaPilot (/settings).
 */
export default function PlatformCommunicationsSettingsPage() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Paramètres e-mail</h2>
          <p>Provider, expéditeur et infrastructure — gérés dans ELFIS Core.</p>
        </div>
      </div>

      <div className="platform-surface-banner">
        <strong>Distinction claire</strong>
        <p>
          <strong>ELFIS Core</strong> : provider, expéditeur, historique global, diagnostic.
          <br />
          <strong>ComptaPilot</strong> : destinataire, sujet, message de facture, document à envoyer.
        </p>
      </div>

      <section className="panel">
        <h3>Infrastructure</h3>
        <p className="muted">
          Les secrets (clé API Brevo, mot de passe SMTP) restent côté serveur. Aucune saisie de secret
          n’est exposée dans cette interface utilisateur.
        </p>
        <div className="platform-surface-banner__actions">
          <Link className="btn" to="/platform/communications">
            Voir l’état des communications
          </Link>
        </div>
      </section>

      <section className="panel">
        <h3>Modèles métier</h3>
        <p className="muted">
          Sujets et messages par défaut des factures / devis : réglages ComptaPilot.
        </p>
        <Link className="btn secondary" to="/settings">
          Ouvrir les modèles ComptaPilot
        </Link>
      </section>
    </div>
  )
}
