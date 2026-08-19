import { useEffect, useId, useRef, useState } from 'react'
import { cx } from '../design-system'

type Workspace = { id: string; name: string }

const DEFAULT_WORKSPACES: Workspace[] = [
  { id: 'main', name: 'Espace principal' },
  { id: 'finance', name: 'Finance' },
  { id: 'sales', name: 'Commercial' },
]

type WorkspaceSwitcherProps = {
  className?: string
  workspaces?: Workspace[]
}

/** Sélecteur d’espace de travail — UI chrome (liste locale / extensible). */
export function WorkspaceSwitcher({
  className,
  workspaces = DEFAULT_WORKSPACES,
}: WorkspaceSwitcherProps) {
  const [open, setOpen] = useState(false)
  const [currentId, setCurrentId] = useState(workspaces[0]?.id ?? 'main')
  const rootRef = useRef<HTMLDivElement>(null)
  const panelId = useId()
  const current = workspaces.find((w) => w.id === currentId) ?? workspaces[0]

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    window.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className={cx('ps-ws', className)} ref={rootRef}>
      <button
        type="button"
        className="ps-ws__trigger"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="ps-ws__label">Workspace</span>
        <strong>{current?.name ?? 'Workspace'}</strong>
      </button>
      {open ? (
        <div className="ps-ws__panel" id={panelId} role="listbox" aria-label="Workspaces">
          {workspaces.map((w) => (
            <button
              key={w.id}
              type="button"
              role="option"
              aria-selected={w.id === currentId}
              className={cx('ps-ws__option', w.id === currentId && 'is-current')}
              onClick={() => {
                setCurrentId(w.id)
                setOpen(false)
              }}
            >
              {w.name}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
