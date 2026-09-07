/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import PublicLayout from './PublicLayout'

vi.mock('../../auth', () => ({
  useAuth: () => ({
    user: { first_name: 'Chris', last_name: 'TAMBA' },
    logout: vi.fn(),
  }),
}))

describe('PublicLayout ELFIS Core', () => {
  afterEach(() => {
    cleanup()
  })

  it('affiche le lockup ELFIS Core, pas ComptaPilot', () => {
    render(
      <MemoryRouter initialEntries={['/abonnement']}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="abonnement" element={<p>Abonnement</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    const brand = screen.getByRole('link', { name: /elfis core — accueil/i })
    expect(brand).toHaveAttribute('href', '/welcome')
    expect(brand.querySelector('img')).toHaveAttribute('src', '/elfis-core-mark.svg')
    expect(screen.getByText('ELFIS Core')).toBeInTheDocument()
    expect(screen.getByText('Plateforme')).toBeInTheDocument()
    const shell = document.querySelector('.public-shell') as HTMLElement
    expect(shell).toBeTruthy()
    expect(shell.getAttribute('data-product')).toBe('elfis-core')
    expect(document.body.textContent).not.toMatch(/ComptaPilot/i)
  })
})
