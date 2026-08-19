/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import {
  OverlayProvider,
  ProductThemeProvider,
  __resetScrollLockForTests,
  getProductById,
} from '../design-system'
import { AppLauncher } from './AppLauncher'
import { ProductMark } from './ProductMark'
import { clearProductEvents, getProductEvents } from '../productEvents'
import type { ReactNode } from 'react'

function resetStorage() {
  try {
    window.localStorage?.removeItem('elfis_last_product')
    window.localStorage?.removeItem('elfis_last_product_at')
  } catch {
    /* ignore */
  }
}

afterEach(() => {
  cleanup()
  __resetScrollLockForTests()
  document.getElementById('elfis-overlay-root')?.remove()
  clearProductEvents()
  resetStorage()
})

function renderLauncher(ui: ReactNode = <AppLauncher />, initialPath = '/home') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ProductThemeProvider
        initialProductId="comptapilot"
        persist={false}
        applyToDom={false}
        resolveFromPath={false}
      >
        <OverlayProvider>
          <Routes>
            <Route path="*" element={ui} />
          </Routes>
        </OverlayProvider>
      </ProductThemeProvider>
    </MemoryRouter>,
  )
}

describe('App Launcher Espaces Hub integration', () => {
  beforeEach(() => {
    resetStorage()
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }),
    })
  })

  it('ouvre depuis trigger Espaces (desktop Dialog)', async () => {
    const user = userEvent.setup()
    renderLauncher()
    const trigger = screen.getByRole('button', { name: /Espaces/i })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(await screen.findByRole('dialog', { name: /hub espaces elfis/i })).toBeInTheDocument()
    expect(screen.getAllByText('Espaces ELFIS').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Finance').length).toBeGreaterThan(0)
  })

  it('Commercial ouvrable; RH bientôt non navigable', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(await screen.findByRole('dialog', { name: /hub espaces elfis/i })).toBeInTheDocument()
    expect(screen.getByText('RH')).toBeInTheDocument()
    expect(screen.getAllByText('Bientôt').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /Ouvrir RH/i })).toBeNull()
    expect(screen.getByRole('button', { name: /Ouvrir Commercial/i })).toBeTruthy()
  })

  it('ferme via Escape et restaure le focus trigger', async () => {
    const user = userEvent.setup()
    renderLauncher()
    const trigger = screen.getByRole('button', { name: /Espaces/i })
    await user.click(trigger)
    await screen.findByRole('dialog', { name: /hub espaces elfis/i })
    await user.keyboard('{Escape}')
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: /hub espaces elfis/i })).toBeNull(),
    )
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('coming soon : RH Analyse Support', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(await screen.findByText('Bientôt disponibles')).toBeInTheDocument()
    expect(screen.getByText('RH')).toBeInTheDocument()
    expect(screen.getByText('Analyse')).toBeInTheDocument()
    expect(screen.getByText('Support')).toBeInTheDocument()
  })

  it('analytics opened / closed / searched', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await screen.findByRole('dialog', { name: /hub espaces elfis/i })
    expect(getProductEvents().some((e) => e.name === 'app_launcher.opened')).toBe(true)
    await user.type(screen.getByPlaceholderText(/rechercher un espace/i), 'Finance')
    await waitFor(() =>
      expect(getProductEvents().some((e) => e.name === 'app_launcher.searched')).toBe(true),
    )
    await user.keyboard('{Escape}')
    await waitFor(() =>
      expect(getProductEvents().some((e) => e.name === 'app_launcher.closed')).toBe(true),
    )
  })

  it('raccourci Ctrl+Shift+A ouvre le launcher (sans voler Ctrl+K)', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.keyboard('{Control>}{Shift>}a{/Shift}{/Control}')
    expect(await screen.findByRole('dialog', { name: /hub espaces elfis/i })).toBeInTheDocument()
  })

  it('navigue vers Commercial sans applyTheme direct', async () => {
    const user = userEvent.setup()
    const applySpy = vi.fn()
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <ProductThemeProvider
          initialProductId="comptapilot"
          persist={false}
          applyToDom={false}
          resolveFromPath={false}
        >
          <OverlayProvider>
            <AppLauncher />
          </OverlayProvider>
        </ProductThemeProvider>
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    const openSales = await screen.findByRole('button', { name: /Ouvrir Commercial/i })
    expect(applySpy).not.toHaveBeenCalled()
    await user.click(openSales)
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: /hub espaces elfis/i })).toBeNull(),
    )
  })

  it('ProductMark fallback initiale', () => {
    const base = getProductById('salespilot')
    const product = {
      ...base,
      logoMark: '',
      branding: { ...base.branding, logoMark: '', logo: '', favicon: '', illustrations: '' },
    }
    render(<ProductMark product={product} />)
    expect(screen.getByRole('img', { name: /SalesPilot/i })).toBeInTheDocument()
    expect(screen.getByText('S')).toBeInTheDocument()
  })

  it('sandbox preview overrides sans muter le registry', async () => {
    const user = userEvent.setup()
    const before = getProductById('docpilot').status
    renderLauncher(
      <AppLauncher
        mode="sandbox_preview"
        previewOverrides={{
          docpilot: { state: 'beta', route: '/sales', canOpen: true },
        }}
      />,
    )
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(await screen.findByRole('dialog', { name: /hub espaces elfis/i })).toBeInTheDocument()
    expect(document.querySelector('[data-space="documents"]')).toBeTruthy()
    expect(getProductById('docpilot').status).toBe(before)
  })

  it('mobile Drawer via matchMedia', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: query.includes('1024'),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }),
    })
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(screen.getAllByText('Espaces ELFIS').length).toBeGreaterThan(0)
  })
})
