/**
 * S1.0 + S1.1 domain separation redirects
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom'

afterEach(() => {
  cleanup()
})

describe('Domain separation redirects', () => {
  it('/quotes → /devis', () => {
    render(
      <MemoryRouter initialEntries={['/quotes']}>
        <Routes>
          <Route path="quotes" element={<Navigate to="/devis" replace />} />
          <Route path="devis" element={<div>Devis OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Devis OK')).toBeInTheDocument()
  })

  it('/catalog → /catalogue', () => {
    render(
      <MemoryRouter initialEntries={['/catalog']}>
        <Routes>
          <Route path="catalog" element={<Navigate to="/catalogue" replace />} />
          <Route path="catalogue" element={<div>Catalogue OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Catalogue OK')).toBeInTheDocument()
  })

  it('/team → /platform/members', () => {
    render(
      <MemoryRouter initialEntries={['/team']}>
        <Routes>
          <Route path="team" element={<Navigate to="/platform/members" replace />} />
          <Route path="platform/members" element={<div>Members OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Members OK')).toBeInTheDocument()
  })

  it('/organisation → /platform/organization', () => {
    render(
      <MemoryRouter initialEntries={['/organisation']}>
        <Routes>
          <Route path="organisation" element={<Navigate to="/platform/organization" replace />} />
          <Route path="platform/organization" element={<div>Org OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Org OK')).toBeInTheDocument()
  })

  it('/admin/equipe → /platform/members', () => {
    render(
      <MemoryRouter initialEntries={['/admin/equipe']}>
        <Routes>
          <Route path="admin/equipe" element={<Navigate to="/platform/members" replace />} />
          <Route path="platform/members" element={<div>Members OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Members OK')).toBeInTheDocument()
  })

  it('/vault → /platform/documents', () => {
    render(
      <MemoryRouter initialEntries={['/vault']}>
        <Routes>
          <Route path="vault" element={<Navigate to="/platform/documents" replace />} />
          <Route path="platform/documents" element={<div>Vault OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Vault OK')).toBeInTheDocument()
  })
})
