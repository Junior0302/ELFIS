import { NavLink, Outlet } from 'react-router-dom'
import './facturation-spaces.css'

const SPACES = [
  { to: '/facturation', end: true, label: 'Vue d’ensemble' },
  { to: '/facturation/documents', end: false, label: 'Documents' },
  { to: '/facturation/catalogue', end: false, label: 'Catalogue' },
  // redirect → /catalogue (Smart Library)
  { to: '/facturation/activite', end: false, label: 'Activité' },
] as const

export default function FacturationLayout() {
  return (
    <div
      className="fp-spaces"
      data-fp-spaces="f10"
      data-fp-focus="false"
      data-fp-full-focus="false"
    >
      <nav className="fp-spaces__nav" aria-label="Espaces Facturation">
        <ul className="fp-spaces__list">
          {SPACES.map((space) => (
            <li key={space.to}>
              <NavLink
                to={space.to}
                end={space.end}
                className={({ isActive }) =>
                  isActive ? 'fp-spaces__link is-active' : 'fp-spaces__link'
                }
              >
                {space.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="fp-spaces__outlet">
        <Outlet />
      </div>
    </div>
  )
}
