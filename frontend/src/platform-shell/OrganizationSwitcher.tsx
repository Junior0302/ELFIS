import { useEffect, useId, useRef, useState } from 'react'
import { useAuth } from '../auth'
import { cx } from '../design-system'
import { closeAllOverlays } from '../design-system/overlays/manager/overlayLifecycle'

type OrganizationSwitcherProps = {
  className?: string
}

export function OrganizationSwitcher({ className }: OrganizationSwitcherProps) {
  const { memberships, orgId, setOrgId } = useAuth()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  const current = memberships.find((m) => m.organization_id === orgId) ?? memberships[0]

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

  if (!memberships.length) {
    return (
      <div className={cx('ps-org', 'ps-org--empty', className)}>
        <span>Aucune organisation</span>
      </div>
    )
  }

  const selectOrg = (id: number) => {
    closeAllOverlays('organization_change')
    setOrgId(id)
    setOpen(false)
  }

  return (
    <div className={cx('ps-org', className)} ref={rootRef}>
      <button
        type="button"
        className="ps-org__trigger"
        aria-expanded={open}
        aria-controls={panelId}
        aria-haspopup="listbox"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="ps-org__label">Organisation</span>
        <strong>{current?.organization_name ?? `Org #${orgId}`}</strong>
      </button>
      {open ? (
        <div className="ps-org__panel" id={panelId} role="listbox" aria-label="Organisations">
          <p className="ps-org__section">Organisation actuelle</p>
          <button
            type="button"
            role="option"
            aria-selected
            className="ps-org__option is-current"
            onClick={() => setOpen(false)}
          >
            {current?.organization_name ?? `Org #${orgId}`}
          </button>
          <p className="ps-org__section">Autres organisations</p>
          {memberships
            .filter((m) => m.organization_id !== current?.organization_id)
            .map((m) => (
              <button
                key={m.organization_id}
                type="button"
                role="option"
                aria-selected={false}
                className="ps-org__option"
                onClick={() => selectOrg(m.organization_id)}
              >
                {m.organization_name}
              </button>
            ))}
          {memberships.length < 2 ? (
            <p className="ps-org__muted">Aucune autre organisation</p>
          ) : null}
          <button type="button" className="ps-org__create" disabled title="Bientôt disponible">
            Créer une organisation
          </button>
        </div>
      ) : null}
    </div>
  )
}
