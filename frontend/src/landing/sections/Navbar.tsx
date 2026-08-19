import { useEffect, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { LandingLogo } from '../components/LandingLogo'

const NAV_LINKS = [
  { href: '#plateforme', label: 'Plateforme' },
  { href: '#solutions', label: 'Solutions' },
  { href: '#tarifs', label: 'Tarifs' },
  { href: '#ressources', label: 'Ressources' },
  { href: '#a-propos', label: 'À propos' },
] as const

type NavbarProps = {
  primaryTo: string
  loginTo: string
  isAuthenticated: boolean
}

export function Navbar({ primaryTo, loginTo, isAuthenticated }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const menuId = useId()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const close = () => setOpen(false)

  return (
    <header className={`landing-nav ${scrolled ? 'is-scrolled' : ''} ${open ? 'is-open' : ''}`}>
      <div className="landing-nav__inner">
        <LandingLogo />

        <button
          type="button"
          className="landing-nav__toggle"
          aria-expanded={open}
          aria-controls={menuId}
          aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'}
          onClick={() => setOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav id={menuId} className="landing-nav__menu" aria-label="Navigation principale">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} onClick={close}>
              {link.label}
            </a>
          ))}
          <div className="landing-nav__actions">
            {isAuthenticated ? (
              <Link className="btn" to={primaryTo} onClick={close}>
                Ouvrir mon espace
              </Link>
            ) : (
              <>
                <Link className="landing-nav__login" to={loginTo} onClick={close}>
                  Connexion
                </Link>
                <Link className="btn" to={primaryTo} onClick={close}>
                  Découvrir ELFIS
                </Link>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}
