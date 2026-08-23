/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AuthLayout from './AuthLayout'
import RegisterPage from '../pages/RegisterPage'
import ForgotPasswordPage from '../pages/ForgotPasswordPage'

vi.mock('../auth', () => ({
  useAuth: () => ({
    register: vi.fn(),
    user: null,
    firebaseReady: true,
  }),
}))

function renderAuth(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="register" element={<RegisterPage />} />
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('AuthLayout ELFIS Core', () => {
  afterEach(() => {
    cleanup()
  })

  it('inscription utilise le chrome ELFIS Core', () => {
    renderAuth('/register')
    expect(document.querySelector('.elfis-login')).toBeTruthy()
    expect(screen.getByRole('heading', { name: /créer un compte/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/prénom/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /créer mon compte/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /se connecter/i })).toHaveAttribute('href', '/login')
    expect(document.body.textContent).not.toMatch(/pilotez vos chiffres/i)
  })

  it('mot de passe oublié utilise le chrome ELFIS Core', () => {
    renderAuth('/forgot-password')
    expect(document.querySelector('.elfis-login')).toBeTruthy()
    expect(screen.getByRole('heading', { name: /mot de passe oublié/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/adresse email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /envoyer le lien/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /retour à la connexion/i })).toHaveAttribute(
      'href',
      '/login',
    )
  })
})
