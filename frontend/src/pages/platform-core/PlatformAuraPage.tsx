import { Link } from 'react-router-dom'
import CopilotePage from '../CopilotePage'
import '../../platform-workspace/platform-workspace.css'

/**
 * Aura — assistant global ELFIS Core.
 * Réutilise le moteur IA existant ; ne crée pas une nouvelle IA.
 */
export default function PlatformAuraPage() {
  return (
    <div className="page platform-aura">
      <div className="platform-surface-banner">
        <strong>Aura · ELFIS Core</strong>
        <p>
          Assistant global de la plateforme. Pour l’analyse TVA, trésorerie et écritures, utilisez
          aussi l’Assistant financier dans ComptaPilot.
        </p>
        <div className="platform-surface-banner__actions">
          <Link className="btn secondary" to="/copilote">
            Assistant financier ComptaPilot
          </Link>
          <Link className="btn secondary" to="/home">
            Retour Home
          </Link>
        </div>
      </div>
      <CopilotePage />
    </div>
  )
}
