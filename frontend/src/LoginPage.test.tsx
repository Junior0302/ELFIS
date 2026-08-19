/**
 * @vitest-environment jsdom
 */
/**
 * Login ELFIS Core V1 — rendu, flux auth, a11y, anti double-submit.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from './pages/LoginPage'

const loginMock = vi.fn()
const navigateMock = vi.fn()

vi.mock('./auth', () => ({
  useAuth: () => ({
    login: loginMock,
    user: null,
    firebaseReady: true,
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

function renderLogin(initialEntry = '/login') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage ELFIS Core V1', () => {
  beforeEach(() => {
    loginMock.mockReset()
    navigateMock.mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  it('rendu ELFIS Core — pas de texte principal ComptaPilot', () => {
    renderLogin()
    expect(screen.getByRole('heading', { name: /^connexion$/i })).toBeInTheDocument()
    expect(screen.getByText(/une connexion\./i)).toBeInTheDocument()
    expect(screen.getByText(/tout votre écosystème/i)).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/pilotez vos chiffres/i)
    expect(screen.getAllByText(/ELFIS Core/i).length).toBeGreaterThan(0)
  })

  it('champs email et mot de passe accessibles', () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('type', 'email')
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('autocomplete', 'email')
    expect(screen.getByLabelText(/^mot de passe/i)).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText(/^mot de passe/i)).toHaveAttribute(
      'autocomplete',
      'current-password',
    )
  })

  it('liens mot de passe oublié, créer un compte, retour landing', () => {
    renderLogin()
    expect(screen.getByRole('link', { name: /mot de passe oublié/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
    expect(screen.getByRole('link', { name: /créer un compte/i })).toHaveAttribute('href', '/register')
    expect(screen.getByRole('link', { name: /retour au site/i })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /retour à l'accueil/i })).toHaveAttribute('href', '/')
  })

  it('login succès → navigue /home et quitte Connexion…', async () => {
    const user = userEvent.setup()
    loginMock.mockResolvedValue(undefined)
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'a@b.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    await waitFor(() => expect(loginMock).toHaveBeenCalledTimes(1))
    expect(loginMock).toHaveBeenCalledWith('a@b.com', 'secret123')
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/home', { replace: true }))
    expect(screen.getByRole('button', { name: /^se connecter$/i })).not.toBeDisabled()
  })

  it('conserve l’email après erreur', async () => {
    const user = userEvent.setup()
    loginMock.mockRejectedValue(Object.assign(new Error('bad'), { code: 'auth/invalid-credential' }))
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'keep@me.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'bad')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    await screen.findByRole('alert')
    expect(screen.getByLabelText(/email/i)).toHaveValue('keep@me.com')
  })

  it('identifiants invalides → message + loading false', async () => {
    const user = userEvent.setup()
    loginMock.mockRejectedValue(Object.assign(new Error('bad'), { code: 'auth/invalid-credential' }))
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'a@b.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'bad')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/incorrect/i)
    expect(screen.getByRole('button', { name: /^se connecter$/i })).not.toBeDisabled()
  })

  it('backend timeout → message serveur', async () => {
    const user = userEvent.setup()
    loginMock.mockRejectedValue(new DOMException('Aborted', 'AbortError'))
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'a@b.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/ne répond pas/i)
    expect(screen.getByRole('button', { name: /^se connecter$/i })).not.toBeDisabled()
  })

  it('double clic bloqué pendant la requête', async () => {
    const user = userEvent.setup()
    let resolveLogin: () => void = () => undefined
    loginMock.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveLogin = resolve
        }),
    )
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'a@b.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    expect(await screen.findByRole('button', { name: /connexion…/i })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: /connexion…/i }))
    expect(loginMock).toHaveBeenCalledTimes(1)
    resolveLogin()
    await waitFor(() => expect(navigateMock).toHaveBeenCalled())
  })

  it('invite → redirection /compte?invite=', async () => {
    const user = userEvent.setup()
    loginMock.mockResolvedValue(undefined)
    renderLogin('/login?invite=tok-123')
    await user.type(screen.getByLabelText(/email/i), 'a@b.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    await waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith('/compte?invite=tok-123', { replace: true }),
    )
    expect(screen.getByRole('link', { name: /créer un compte/i })).toHaveAttribute(
      'href',
      '/register?invite=tok-123',
    )
  })

  it('redirection vers route protégée précédente (state.from)', async () => {
    const user = userEvent.setup()
    loginMock.mockResolvedValue(undefined)
    render(
      <MemoryRouter initialEntries={[{ pathname: '/login', state: { from: '/sales' } }]}>
        <LoginPage />
      </MemoryRouter>,
    )
    await user.type(screen.getByLabelText(/email/i), 'a@b.com')
    await user.type(screen.getByLabelText(/^mot de passe/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /^se connecter$/i }))
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/sales', { replace: true }))
  })

  it('structure mobile : formulaire présent, marque ELFIS', () => {
    renderLogin()
    const card = screen.getByRole('heading', { name: /^connexion$/i }).closest('.elfis-login__card')
    expect(card).toBeTruthy()
    expect(within(card as HTMLElement).getByRole('button', { name: /se connecter/i })).toBeInTheDocument()
    expect(document.querySelector('.elfis-login__illu')).toBeTruthy()
  })

  it('prefers-reduced-motion : classes d’animation présentes (CSS gère la coupure)', () => {
    renderLogin()
    expect(document.querySelector('.elfis-login__illu-ring')).toBeTruthy()
    expect(document.querySelector('.elfis-login')).toBeTruthy()
  })
})
