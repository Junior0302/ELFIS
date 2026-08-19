/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import FacturationLayout from '../../comptapilot/facturation/FacturationLayout'

function renderAt(path: string) {
  cleanup()
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/facturation" element={<FacturationLayout />}>
          <Route index element={<div>overview-space</div>} />
          <Route
            path="documents"
            element={
              <>
                <div>documents-space</div>
                <Outlet />
              </>
            }
          >
            <Route path="new" element={<div>composer-modal-marker</div>} />
          </Route>
          <Route path="nouveau" element={<div>nouveau-space</div>} />
          <Route path="catalogue" element={<div>redirect-catalogue</div>} />
          <Route path="activite" element={<div>redirect-activite</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('Facturation spaces F1.3.1 routes', () => {
  it('expose la nav des 4 espaces (sans Nouveau document)', () => {
    renderAt('/facturation')
    expect(screen.getByRole('navigation', { name: /espaces facturation/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /vue d’ensemble/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^documents$/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /nouveau document/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^catalogue$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^activité$/i })).toBeInTheDocument()
  })

  it('rend l’outlet overview', () => {
    renderAt('/facturation')
    expect(screen.getByText('overview-space')).toBeInTheDocument()
  })

  it('rend l’outlet documents', () => {
    renderAt('/facturation/documents')
    expect(screen.getByText('documents-space')).toBeInTheDocument()
  })

  it('rend documents + marker nested /new', () => {
    renderAt('/facturation/documents/new')
    expect(screen.getByText('documents-space')).toBeInTheDocument()
    expect(screen.getByText('composer-modal-marker')).toBeInTheDocument()
  })

  it('conserve la nav Facturation sous /documents/new (modal, pas full-focus page)', () => {
    renderAt('/facturation/documents/new')
    const root = document.querySelector('[data-fp-spaces="f10"]')
    expect(root).toBeTruthy()
    expect(root).not.toHaveClass('fp-spaces--full-focus')
    expect(root).toHaveAttribute('data-fp-full-focus', 'false')
    const nav = document.querySelector('.fp-spaces__nav')
    expect(nav).toBeTruthy()
    expect(nav).not.toHaveAttribute('hidden')
  })
})
