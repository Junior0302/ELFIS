import { Link } from 'react-router-dom'
import { useProductTheme } from '../design-system/themes/ProductThemeProvider'
import type { ProductId } from '../design-system'
import { PlatformShell } from '../platform-shell'

const DEMO_LINKS = [
  { label: 'Vue d’ensemble', active: true },
  { label: 'Activité', active: false },
  { label: 'Réglages Pilot', active: false },
]

/**
 * Démonstration du Platform Shell officiel (chrome only).
 * Aucun métier CRM / compta — viewport placeholder.
 */
export default function PlatformShellDemoPage() {
  const { currentProductId } = useProductTheme()
  const productId = (currentProductId || 'elfis-core') as ProductId

  return (
    <PlatformShell
      productId={productId === 'elfis-core' ? 'comptapilot' : productId}
      sidebarTitle="Navigation (démo)"
      sidebar={
        <ul className="ps-demo-nav">
          {DEMO_LINKS.map((item) => (
            <li key={item.label}>
              {item.active ? (
                <span className="is-active">{item.label}</span>
              ) : (
                <a href="#platform-workspace">{item.label}</a>
              )}
            </li>
          ))}
          <li>
            <Link to="/">← Landing</Link>
          </li>
        </ul>
      }
    >
      <div className="ps-demo-card">
        <h1>Platform Shell V1</h1>
        <p>
          Chrome permanent ELFIS Core : topbar, launcher, recherche (UI), notifications (mock),
          organisation, workspace, profil. Le contenu métier des Pilot s’affiche ici via{' '}
          <code>WorkspaceViewport</code>.
        </p>
      </div>
    </PlatformShell>
  )
}
