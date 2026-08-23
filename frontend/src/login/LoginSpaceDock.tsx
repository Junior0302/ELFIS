import { getAvailableWorkspaces } from '../workspaces'
import { WorkspaceSpaceIcon } from '../workspaces/WorkspaceSpaceIcon'

/**
 * Dock visuel des espaces ouverts — décoratif sur /login (pas de deep-link métier).
 */
export function LoginSpaceDock() {
  const spaces = getAvailableWorkspaces()

  return (
    <ul className="elfis-login__dock" aria-label="Espaces ELFIS disponibles">
      {spaces.map((space) => (
        <li key={space.id} title={space.label}>
          <WorkspaceSpaceIcon
            icon={space.icon}
            accent={space.accent.primary}
            soft={space.accent.soft}
            size="sm"
          />
          <span className="visually-hidden">{space.label}</span>
        </li>
      ))}
      <li className="elfis-login__dock-more" title="D’autres espaces arrivent">
        <span aria-hidden>+</span>
        <span className="visually-hidden">Autres espaces à venir</span>
      </li>
    </ul>
  )
}
