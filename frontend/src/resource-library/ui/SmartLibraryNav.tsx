import type { LibraryNavSection } from '../types'
import type { ResourceSource } from '../sources/resourceSource'

const SECTIONS: {
  id: LibraryNavSection
  label: string
  requires?: keyof ResourceSource['capabilities']
  alwaysDisabled?: boolean
}[] = [
  { id: 'all', label: 'Tous' },
  { id: 'products', label: 'Produits' },
  { id: 'services', label: 'Services' },
  { id: 'packs', label: 'Packs', requires: 'packs' },
  { id: 'favorites', label: 'Favoris', requires: 'favorites' },
  { id: 'recents', label: 'Récents', requires: 'recents' },
  { id: 'most_used', label: 'Plus utilisés', requires: 'mostUsed' },
]

export type SmartLibraryNavProps = {
  section: LibraryNavSection
  onChange: (section: LibraryNavSection) => void
  source: ResourceSource
}

export function SmartLibraryNav({ section, onChange, source }: SmartLibraryNavProps) {
  return (
    <nav className="sl-nav" aria-label="Sections Smart Library">
      {SECTIONS.map((s) => {
        const disabled = s.requires ? !source.capabilities[s.requires] : false
        return (
          <button
            key={s.id}
            type="button"
            className={[
              section === s.id ? 'is-active' : '',
              disabled ? 'is-disabled' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-current={section === s.id ? 'page' : undefined}
            disabled={disabled && s.id !== section}
            title={
              disabled
                ? 'Section indisponible — aucune donnée réelle exposée'
                : undefined
            }
            onClick={() => onChange(s.id)}
          >
            <span>{s.label}</span>
            {disabled ? <span className="sl-nav__hint">Bientôt</span> : null}
          </button>
        )
      })}
    </nav>
  )
}
