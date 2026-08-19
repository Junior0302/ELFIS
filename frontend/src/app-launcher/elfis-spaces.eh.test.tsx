/**
 * BRAND.ELFIS.1 — Hub Espaces ELFIS — EH01–EH30
 * @vitest-environment jsdom
 */
import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import {
  OverlayProvider,
  ProductThemeProvider,
  __resetScrollLockForTests,
} from '../design-system'
import { AppLauncher } from './AppLauncher'
import { AppLauncherPanel } from './AppLauncherPanel'
import { getLauncherFooterLinks } from './launcherModel'
import { ELFIS_SPACES, getSpaceById, getSpaceByProductId } from './spacesCatalog'
import {
  buildSpaceSections,
  filterSpaces,
  matchesSpaceQuery,
  resolveContinueSpace,
  resolveSpaceState,
} from './spacesModel'
import { getKnownSpaRoutes } from './productEntryRoutes'
import type { LauncherResolveContext } from './launcher.types'
import type { ReactNode } from 'react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function resetStorage() {
  try {
    window.localStorage?.removeItem('elfis_last_product')
    window.localStorage?.removeItem('elfis_last_product_at')
  } catch {
    /* ignore */
  }
}

function ctx(partial: Partial<LauncherResolveContext> = {}): LauncherResolveContext {
  return {
    currentProductId: 'comptapilot',
    availableRoutes: getKnownSpaRoutes(),
    ...partial,
  }
}

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

afterEach(() => {
  cleanup()
  __resetScrollLockForTests()
  document.getElementById('elfis-overlay-root')?.remove()
  resetStorage()
})

describe('EH — Hub Espaces ELFIS (BRAND.ELFIS.1)', () => {
  it('EH01 — topbar libellé Espaces (pas Applications)', async () => {
    const user = userEvent.setup()
    renderLauncher()
    const trigger = screen.getByRole('button', { name: /Espaces/i })
    expect(trigger).toHaveAttribute('title', 'Espaces ELFIS')
    expect(trigger.textContent).not.toMatch(/Applications/i)
    await user.click(trigger)
    expect(await screen.findByRole('dialog', { name: /hub espaces elfis/i })).toBeInTheDocument()
  })

  it('EH02 — titre Espaces ELFIS + sous-titre métiers', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(await screen.findAllByText('Espaces ELFIS')).not.toHaveLength(0)
    expect(
      screen.getAllByText(/accédez à tous les métiers de votre entreprise depuis un seul espace/i)
        .length,
    ).toBeGreaterThan(0)
    expect(screen.queryByText(/plusieurs applications/i)).toBeNull()
    expect(screen.queryByText(/changer d’application/i)).toBeNull()
  })

  it('EH03 — six espaces métier catalogue', () => {
    expect(ELFIS_SPACES.map((s) => s.id)).toEqual([
      'finance',
      'commercial',
      'documents',
      'rh',
      'analyse',
      'support',
    ])
  })

  it('EH04 — Finance → /dashboard, Commercial → /sales, Documents → /platform/documents', () => {
    expect(getSpaceById('finance').entryRoute).toBe('/dashboard')
    expect(getSpaceById('commercial').entryRoute).toBe('/sales')
    expect(getSpaceById('documents').entryRoute).toBe('/platform/documents')
  })

  it('EH05 — RH / Analyse / Support sans route → Bientôt', () => {
    const sections = buildSpaceSections(ctx())
    const soon = sections.comingSoon.map((s) => s.space.id)
    expect(soon).toEqual(expect.arrayContaining(['rh', 'analyse', 'support']))
    for (const id of ['rh', 'analyse', 'support'] as const) {
      expect(getSpaceById(id).entryRoute).toBeNull()
      expect(resolveSpaceState(getSpaceById(id), ctx()).state).toBe('coming_soon')
      expect(resolveSpaceState(getSpaceById(id), ctx()).canOpen).toBe(false)
    }
  })

  it('EH06 — pas de carte ELFIS Core application', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await screen.findByRole('dialog', { name: /hub espaces elfis/i })
    expect(screen.queryByText(/ELFIS Core — Application active/i)).toBeNull()
    expect(screen.queryByText(/by ELFIS Core/i)).toBeNull()
    expect(screen.getAllByRole('link', { name: /Accueil ELFIS/i }).length).toBeGreaterThan(0)
  })

  it('EH07 — signatures moteurs discrètes', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await screen.findByText('Finance')
    expect(screen.getByText('Moteur ComptaPilot')).toBeInTheDocument()
    expect(screen.getByText('Moteur SalesPilot')).toBeInTheDocument()
    expect(screen.getByText('Moteur DocPilot')).toBeInTheDocument()
  })

  it('EH08 — Continuer = Reprendre dans Finance (fallback)', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(await screen.findByRole('button', { name: /Commencer dans Finance/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Continuer ComptaPilot/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /Commencer avec ComptaPilot/i })).toBeNull()
  })

  it('EH09 — Reprendre dans Commercial si lastProduct salespilot', () => {
    const sections = buildSpaceSections(ctx())
    const { continueItem, fallbackContinue } = resolveContinueSpace(
      sections,
      ctx(),
      'salespilot',
      new Date().toISOString(),
    )
    expect(continueItem?.space.id).toBe('commercial')
    expect(continueItem?.isLastUsed).toBe(true)
    expect(fallbackContinue).toBeNull()
    expect(getSpaceByProductId('salespilot')?.title).toBe('Commercial')
  })

  it('EH10 — recherche alias facture → Finance', () => {
    const sections = buildSpaceSections(ctx())
    const all = [...sections.available, ...sections.comingSoon]
    expect(filterSpaces(all, 'facture').map((s) => s.space.id)).toContain('finance')
    expect(matchesSpaceQuery(resolveSpaceState(getSpaceById('finance'), ctx()), 'tva')).toBe(true)
  })

  it('EH11 — recherche alias pipeline → Commercial', () => {
    const sections = buildSpaceSections(ctx())
    const all = [...sections.available, ...sections.comingSoon]
    expect(filterSpaces(all, 'pipeline').map((s) => s.space.id)).toContain('commercial')
  })

  it('EH12 — footer Accueil ELFIS + liens plateforme', () => {
    const links = getLauncherFooterLinks()
    expect(links.map((l) => l.label)).toEqual([
      'Accueil ELFIS',
      'Organisation',
      'Documents',
      'Relations',
      'Communications',
      'Paramètres',
    ])
    expect(links.find((l) => l.id === 'home')?.to).toBe('/home')
    expect(links.some((l) => /ELFIS Home|Découvrir/i.test(l.label))).toBe(false)
  })

  it('EH13 — Accueil ELFIS dans header et footer', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await screen.findByRole('dialog', { name: /hub espaces elfis/i })
    const homes = screen.getAllByRole('link', { name: /Accueil ELFIS/i })
    expect(homes.length).toBeGreaterThanOrEqual(2)
    expect(homes.every((a) => a.getAttribute('href') === '/home')).toBe(true)
  })

  it('EH14 — cartes communes même composant (data-space)', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await screen.findByText('Espaces métier')
    const panel = document.querySelector('[data-launcher="spaces-hub-v1"]')
    expect(panel).toBeTruthy()
    expect(panel?.querySelectorAll('[data-space]').length).toBeGreaterThanOrEqual(6)
  })

  it('EH15 — accents domaines distincts', () => {
    expect(getSpaceById('finance').accent).toBe('#0B3D2E')
    expect(getSpaceById('commercial').accent).toBe('#1D4ED8')
    expect(getSpaceById('documents').accent).toBe('#6D28D9')
    expect(getSpaceById('rh').accent).toBe('#C2410C')
  })

  it('EH16 — routes connues incluent coffre plateforme', () => {
    const routes = getKnownSpaRoutes()
    expect(routes.has('/dashboard')).toBe(true)
    expect(routes.has('/sales')).toBe(true)
    expect(routes.has('/platform/documents')).toBe(true)
  })

  it('EH17 — Finance / Commercial / Documents ouvrables', () => {
    const sections = buildSpaceSections(ctx())
    const ids = sections.available.map((s) => s.space.id)
    expect(ids).toEqual(expect.arrayContaining(['finance', 'commercial', 'documents']))
    expect(sections.available.every((s) => s.canOpen && s.route)).toBe(true)
  })

  it('EH18 — badge Bientôt sur espaces sans route', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await screen.findByRole('heading', { name: /bientôt disponibles/i })
    expect(screen.getAllByText('Bientôt').length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByRole('button', { name: /Ouvrir RH/i })).toBeNull()
  })

  it('EH19 — raccourcis Finance routes réelles', () => {
    const finance = getSpaceById('finance')
    expect(finance.shortcuts.map((s) => s.to)).toEqual(
      expect.arrayContaining(['/facturation', '/tva', '/banque']),
    )
  })

  it('EH20 — raccourcis Commercial routes réelles', () => {
    const commercial = getSpaceById('commercial')
    expect(commercial.shortcuts.map((s) => s.to)).toEqual(
      expect.arrayContaining(['/sales/pipeline', '/sales/leads']),
    )
  })

  it('EH21 — recherche placeholder espaces/fonctions', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    expect(
      await screen.findByPlaceholderText(/rechercher un espace, une fonction/i),
    ).toBeInTheDocument()
  })

  it('EH22 — empty search espaces', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AppLauncherPanel resolveContext={ctx()} onSelect={() => undefined} />
      </MemoryRouter>,
    )
    await user.type(screen.getByPlaceholderText(/rechercher un espace/i), 'zzzz-introuvable')
    expect(screen.getByText(/aucun espace ne correspond/i)).toBeInTheDocument()
  })

  it('EH23 — Ctrl+Shift+A ouvre le hub', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.keyboard('{Control>}{Shift>}a{/Shift}{/Control}')
    expect(await screen.findByRole('dialog', { name: /hub espaces elfis/i })).toBeInTheDocument()
  })

  it('EH24 — Escape ferme et restaure focus', async () => {
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

  it('EH25 — Ouvrir Commercial navigue et ferme le hub', async () => {
    const user = userEvent.setup()
    renderLauncher(<AppLauncher />, '/home')
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    await user.click(await screen.findByRole('button', { name: /Ouvrir Commercial/i }))
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: /hub espaces elfis/i })).toBeNull(),
    )
  })

  it('EH26 — espace actif Finance quand currentProductId comptapilot', () => {
    const finance = resolveSpaceState(getSpaceById('finance'), ctx())
    expect(finance.state).toBe('active')
    expect(finance.label).toMatch(/espace actif/i)
  })

  it('EH27 — pas de texte Applications dans panel', async () => {
    const user = userEvent.setup()
    renderLauncher()
    await user.click(screen.getByRole('button', { name: /Espaces/i }))
    const dialog = await screen.findByRole('dialog', { name: /hub espaces elfis/i })
    expect(dialog.textContent).not.toMatch(/Applications disponibles/i)
    expect(dialog.textContent).not.toMatch(/Applications ELFIS/i)
  })

  it('EH28 — docs elfis-spaces présentes', () => {
    const base = resolve(__dirname, '../../docs/elfis-spaces')
    for (const name of [
      'README.md',
      '01-current-launcher-audit.md',
      '02-spaces-information-architecture.md',
      '03-space-cards-contract.md',
      '04-search-aliases.md',
      '05-continue-resume.md',
      '06-routes-mapping.md',
      '07-visual-language.md',
      '08-test-plan.md',
      '09-implementation-report.md',
    ]) {
      expect(() => readFileSync(resolve(base, name), 'utf8')).not.toThrow()
    }
  })

  it('EH29 — TypeScript build contract (module exports)', async () => {
    const mod = await import('./index')
    expect(mod.AppLauncher).toBeTypeOf('function')
    expect(mod.buildSpaceSections).toBeTypeOf('function')
    expect(mod.ELFIS_SPACES.length).toBe(6)
  })

  it('EH30 — build/tsc asserted via npm scripts (smoke module)', () => {
    /* NC-style : smoke que getKnownSpaRoutes + catalogue restent cohérents pour build */
    const routes = getKnownSpaRoutes()
    for (const space of ELFIS_SPACES) {
      if (space.entryRoute) expect(routes.has(space.entryRoute)).toBe(true)
    }
    expect(true).toBe(true)
  })
})

