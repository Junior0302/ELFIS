import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { findNavItem } from '../navConfig'

const GUIDE_KEY = 'cp_page_guide_open'

export default function PageGuide() {
  const { pathname } = useLocation()
  const item = findNavItem(pathname)
  const [open, setOpen] = useState(() => {
    try {
      return localStorage.getItem(GUIDE_KEY) !== '0'
    } catch {
      return true
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(GUIDE_KEY, open ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [open])

  if (!item) return null

  return (
    <aside className={`page-guide ${open ? '' : 'is-collapsed'}`} aria-label={`À propos de ${item.label}`}>
      <div className="page-guide-head">
        <div>
          <p className="page-guide-kicker">Guide · {item.label}</p>
          <p className="page-guide-spoken">{item.spokenIntro}</p>
        </div>
        <div className="page-guide-actions">
          <button
            type="button"
            className="page-guide-toggle"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
          >
            {open ? 'Masquer' : 'Détails'}
          </button>
        </div>
      </div>
      {open && (
        <ol className="page-guide-list">
          {item.guide.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      )}
    </aside>
  )
}
