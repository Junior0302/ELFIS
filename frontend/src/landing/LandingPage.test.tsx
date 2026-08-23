/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { LandingPage } from './LandingPage'

const authState = { user: null as { id: number } | null }

vi.mock('../auth', () => ({
  useAuth: () => ({
    user: authState.user,
    firebaseReady: true,
  }),
}))

const PILOT_NAME = /ComptaPilot|SalesPilot|DocPilot|HRPilot|AnalyticsPilot|SupportPilot/

function renderLanding() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  )
}

describe('LandingPage — page institutionnelle', () => {
  beforeEach(() => {
    authState.user = null
  })

  afterEach(() => {
    cleanup()
  })

  it('n’expose aucun vocabulaire Pilot ni page Tarifs', () => {
    renderLanding()
    expect(document.body.textContent).not.toMatch(PILOT_NAME)
    expect(screen.queryByRole('link', { name: /tarifs/i })).toBeNull()
  })

  it('hero, Espaces ouverts et CTA fondations', () => {
    renderLanding()
    const hero = screen
      .getByRole('heading', { name: /le système de gestion qui relie votre entreprise/i })
      .closest('section')
    expect(hero).toBeTruthy()
    expect(screen.getByText('ELFIS CORE')).toBeInTheDocument()
    expect(
      screen.getAllByText('Une plateforme. Une organisation. Plusieurs expertises.').length,
    ).toBeGreaterThan(0)
    expect(within(hero!).getByRole('link', { name: /découvrir elfis/i })).toHaveAttribute(
      'href',
      '#produit',
    )
    expect(within(hero!).getByRole('link', { name: /^commencer$/i })).toHaveAttribute(
      'href',
      '/register',
    )
    expect(within(hero!).getByRole('link', { name: /se connecter/i })).toHaveAttribute(
      'href',
      '/login',
    )
    expect(screen.getAllByText('Finance').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Commercial').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Documents').length).toBeGreaterThan(0)
    expect(screen.getByText('Pilotage financier et trésorerie.')).toBeInTheDocument()
    expect(screen.getByText('Ventes et relation client.')).toBeInTheDocument()
    expect(screen.getByText('Centralisation et intelligence documentaire.')).toBeInTheDocument()
  })

  it('navigation desktop : Produit Espaces Solutions Sécurité', () => {
    renderLanding()
    const header = screen.getByRole('banner')
    const nav = within(header).getByRole('navigation', { name: /navigation principale/i })
    expect(within(nav).getByRole('link', { name: /^produit$/i })).toHaveAttribute('href', '#produit')
    expect(within(nav).getByRole('link', { name: /^espaces$/i })).toHaveAttribute('href', '#espaces')
    expect(within(nav).getByRole('link', { name: /^solutions$/i })).toHaveAttribute(
      'href',
      '#solutions',
    )
    expect(within(nav).getByRole('link', { name: /^sécurité$/i })).toHaveAttribute(
      'href',
      '#securite',
    )
  })

  it('menu mobile reste accessible', async () => {
    const user = userEvent.setup()
    renderLanding()
    const toggle = screen.getByRole('button', { name: /ouvrir le menu/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await user.click(toggle)
    expect(screen.getByRole('button', { name: /fermer le menu/i })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    const header = screen.getByRole('banner')
    const nav = within(header).getByRole('navigation', { name: /navigation principale/i })
    expect(within(nav).getByRole('link', { name: /^produit$/i })).toBeVisible()
    expect(within(nav).getByRole('link', { name: /se connecter/i })).toHaveAttribute('href', '/login')
    expect(within(nav).getByRole('link', { name: /^commencer$/i })).toHaveAttribute(
      'href',
      '/register',
    )
  })

  it('utilisateur authentifié : Ouvrir mon espace → /home', () => {
    authState.user = { id: 1 }
    renderLanding()
    const openLinks = screen.getAllByRole('link', { name: /ouvrir mon espace/i })
    expect(openLinks.length).toBeGreaterThan(0)
    expect(openLinks.every((link) => link.getAttribute('href') === '/home')).toBe(true)
    expect(screen.queryByRole('link', { name: /^commencer$/i })).toBeNull()
    expect(screen.getAllByRole('link', { name: /découvrir elfis/i }).every((link) => link.getAttribute('href') === '#produit')).toBe(true)
  })

  it('présente le récit institutionnel et les Espaces à venir', () => {
    renderLanding()
    expect(
      screen.getByRole('heading', {
        name: /votre entreprise ne devrait pas fonctionner comme une collection d’outils isolés/i,
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /une plateforme commune pour toute votre organisation/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', {
        name: /chaque métier possède son espace/i,
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /de l’opportunité au paiement/i })).toBeInTheDocument()
    expect(screen.getByText('Commercial → Documents → Finance')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /votre entreprise mérite un environnement maîtrisé/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /l’écosystème elfis continue de grandir/i })).toBeInTheDocument()
    expect(screen.getByText('Achats')).toBeInTheDocument()
    expect(screen.getByText('Stock & Inventaire')).toBeInTheDocument()
    expect(screen.getByText('Logistique')).toBeInTheDocument()
    expect(screen.getByText('Ressources Humaines')).toBeInTheDocument()
    expect(screen.getByText('Planning')).toBeInTheDocument()
    expect(screen.getByText('Projets')).toBeInTheDocument()
    expect(screen.getByText('Conformité')).toBeInTheDocument()
    expect(screen.getByText('RSE')).toBeInTheDocument()
    expect(
      screen.getByText(/ne doivent pas être considérés comme déjà disponibles/i),
    ).toBeInTheDocument()
  })
})
