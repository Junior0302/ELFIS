/**
 * BRAND.ELFIS.2 — Identité ELFIS + rôles globaux — EB01–EB30
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  GLOBAL_ROLE_DEFS,
  GLOBAL_ROLE_LABELS_FR,
  GLOBAL_ROLE_ORDER,
  BACKEND_ROLE_TO_GLOBAL,
  inviteRoleOptions,
  globalRoleLabel,
  SPACE_ACCESS_COLUMN_ENABLED,
} from './globalRoles'
import { ELFIS_BRAND_COLORS as BrandColors } from '../design-system/colors/elfisBrandTokens'
import { buildPilotTokens, PRODUCT_PALETTES } from '../design-system'
import { ELFIS_NAV_BRAND } from '../platform-shell/global-nav/elfisNavigationConfig'

vi.mock('../auth', () => ({
  useAuth: () => ({
    token: 't',
    orgId: 1,
    user: { id: 1, first_name: 'Chris', last_name: 'Demo', email: 'demo@elfis.test' },
    memberships: [
      {
        organization_id: 1,
        organization_name: 'Acme',
        role: 'admin',
        permissions: ['*', 'users.manage'],
      },
    ],
  }),
}))

vi.mock('../firebase', () => ({
  saveFirestoreOrganizationMember: vi.fn(),
  deleteFirestoreOrganizationMember: vi.fn(),
}))

vi.mock('../api', () => ({
  api: {
    orgMembers: vi.fn(async () => ({
      members: [
        {
          membership_id: 1,
          user_id: 99,
          email: 'owner@elfis.test',
          display_name: 'Owner',
          first_name: 'O',
          last_name: 'W',
          role: 'owner',
          status: 'active',
          permissions: ['*'],
          joined_at: '2024-01-01',
          uid: 'u1',
          avatar: '',
        },
        {
          membership_id: 2,
          user_id: 2,
          email: 'collab@elfis.test',
          display_name: 'Collab',
          first_name: 'C',
          last_name: 'L',
          role: 'employe',
          status: 'active',
          permissions: [],
          joined_at: '2024-02-01',
          uid: 'u2',
          avatar: '',
        },
      ],
      roles: ['admin', 'cfo', 'comptable', 'employe', 'auditeur'],
      can_manage: true,
      can_invite: true,
      plan: 'pro',
      seats: { active: 2, pending_invites: 0, used: 2 },
      seat_limit_message: '',
    })),
    orgInvitations: vi.fn(async () => ({ invitations: [] })),
    inviteOrgMember: vi.fn(),
    updateOrgMember: vi.fn(),
    deleteOrgMember: vi.fn(),
    resendOrgInvitation: vi.fn(),
    cancelOrgInvitation: vi.fn(),
  },
}))

import AdminEquipePage from '../pages/AdminEquipePage'

const docsDir = resolve(__dirname, '../../docs/elfis-brand')
const membersCss = resolve(__dirname, '../pages/elfis-members.css')
const brandCss = resolve(__dirname, '../design-system/colors/elfis-brand.css')
const gnavCss = resolve(__dirname, '../platform-shell/global-nav/elfis-global-navigation.css')
const indexCss = resolve(__dirname, '../index.css')

function renderMembers() {
  return render(
    <MemoryRouter initialEntries={['/platform/members']}>
      <Routes>
        <Route path="/platform/members" element={<AdminEquipePage />} />
        <Route path="/platform/organization" element={<div>org</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('EB — Identité ELFIS (BRAND.ELFIS.2)', () => {
  beforeEach(() => cleanup())
  afterEach(() => cleanup())

  it('EB01 — aucun vert Finance sur invitation membres', () => {
    const css = readFileSync(indexCss, 'utf8')
    const inviteBlock = css.match(/\.member-invite\s*\{[^}]+\}/)?.[0] || ''
    expect(inviteBlock).not.toMatch(/123,\s*196,\s*160|#7bc4a0|#0b3d2e/i)
    expect(inviteBlock).toMatch(/elfis-surface|ffffff/i)
    const brand = readFileSync(brandCss, 'utf8')
    expect(brand).toMatch(/\.member-invite/)
    expect(brand).toMatch(/--elfis-surface/)
  })

  it('EB02 — PageHeader ELFIS', async () => {
    renderMembers()
    expect(await screen.findByText('ENTREPRISE')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /membres et équipes/i })).toBeInTheDocument()
    expect(screen.getByText(/gérez leurs accès à ELFIS/i)).toBeInTheDocument()
    expect(screen.queryByText(/Admin · Équipe/i)).toBeNull()
  })

  it('EB03 — bouton invitation ELFIS', async () => {
    renderMembers()
    expect(await screen.findByRole('button', { name: /envoyer l’invitation/i })).toBeInTheDocument()
  })

  it('EB04 — focus champs ELFIS (blue-600)', () => {
    const css = readFileSync(brandCss, 'utf8')
    expect(css).toMatch(/--elfis-blue-600:\s*#2764e7/i)
    expect(css).toMatch(/pilot-focus:\s*var\(--elfis-blue-600\)/)
    expect(BrandColors.blue600.toLowerCase()).toBe('#2764e7')
  })

  it('EB05 — table neutre', async () => {
    renderMembers()
    await waitFor(() => expect(screen.getByText('owner@elfis.test')).toBeInTheDocument())
    expect(document.querySelector('[data-elfis-table="v1"]')).toBeTruthy()
    expect(screen.getAllByText(/rôle ELFIS/i).length).toBeGreaterThanOrEqual(1)
  })

  it('EB06 — rôle Propriétaire', () => {
    expect(GLOBAL_ROLE_DEFS.owner.label).toBe('Propriétaire')
    expect(GLOBAL_ROLE_DEFS.owner.protected).toBe(true)
  })

  it('EB07 — rôle Administrateur', () => {
    expect(GLOBAL_ROLE_DEFS.admin.label).toBe('Administrateur')
  })

  it('EB08 — rôle Gestionnaire', () => {
    expect(GLOBAL_ROLE_DEFS.manager.label).toBe('Gestionnaire')
    expect(globalRoleLabel('cfo')).toBe('Gestionnaire')
  })

  it('EB09 — rôle Collaborateur', () => {
    expect(GLOBAL_ROLE_DEFS.member.label).toBe('Collaborateur')
    expect(globalRoleLabel('employe')).toBe('Collaborateur')
    expect(globalRoleLabel('comptable')).toBe('Collaborateur')
  })

  it('EB10 — rôle Lecteur', () => {
    expect(GLOBAL_ROLE_DEFS.viewer.label).toBe('Lecteur')
    expect(globalRoleLabel('auditeur')).toBe('Lecteur')
  })

  it('EB11 — Directeur Finance absent des rôles globaux', () => {
    const labels = Object.values(GLOBAL_ROLE_LABELS_FR).join(' ')
    expect(labels).not.toMatch(/Directeur/i)
    expect(GLOBAL_ROLE_ORDER.map((id) => GLOBAL_ROLE_DEFS[id].label).join(' ')).not.toMatch(
      /Directeur/i,
    )
  })

  it('EB12 — Comptable absent des rôles globaux UI', () => {
    const visible = GLOBAL_ROLE_ORDER.map((id) => GLOBAL_ROLE_DEFS[id].label)
    expect(visible).not.toContain('Comptable')
    expect(visible).toEqual([
      'Propriétaire',
      'Administrateur',
      'Gestionnaire',
      'Collaborateur',
      'Lecteur',
    ])
  })

  it('EB13 — descriptions non financières', () => {
    const texts = GLOBAL_ROLE_ORDER.map((id) => GLOBAL_ROLE_DEFS[id].description).join(' ')
    expect(texts).not.toMatch(/facture|fiscalité|banque|comptable/i)
  })

  it('EB14 — sidebar navy tokens', () => {
    expect(BrandColors.navy950.toLowerCase()).toBe('#071629')
    expect(PRODUCT_PALETTES['elfis-core'].primaryColor.toLowerCase()).toBe('#071629')
    const css = readFileSync(gnavCss, 'utf8')
    expect(css).toMatch(/elfis-navy-950|071629|0b1f3a/i)
  })

  it('EB15 — état actif ELFIS (blue-600)', () => {
    const css = readFileSync(gnavCss, 'utf8')
    expect(css).toMatch(/elfis-gnav-accent:\s*var\(--elfis-blue-600/)
  })

  it('EB16 — drawer cohérent navy', () => {
    const css = readFileSync(gnavCss, 'utf8')
    expect(css).toMatch(/linear-gradient\(180deg,\s*var\(--elfis-navy-950/)
  })

  it('EB17 — Organisation lien Membres', () => {
    const org = readFileSync(resolve(__dirname, '../pages/OrganisationPage.tsx'), 'utf8')
    expect(org).toMatch(/\/platform\/members/)
    expect(org).not.toMatch(/Admin → Équipe/)
  })

  it('EB18 — Relations / docs brand', () => {
    expect(existsSync(resolve(docsDir, '03-department-accent-rules.md'))).toBe(true)
    expect(readFileSync(resolve(docsDir, '03-department-accent-rules.md'), 'utf8')).toMatch(
      /Relations/,
    )
  })

  it('EB19 — Documents plateforme documentés', () => {
    expect(readFileSync(resolve(docsDir, '01-runtime-color-audit.md'), 'utf8')).toMatch(
      /platform\/documents/,
    )
  })

  it('EB20 — Communications documentées', () => {
    expect(readFileSync(resolve(docsDir, '01-runtime-color-audit.md'), 'utf8')).toMatch(
      /communications/i,
    )
  })

  it('EB21 — Paramètres / brand docs', () => {
    expect(existsSync(resolve(docsDir, 'README.md'))).toBe(true)
    expect(readFileSync(resolve(docsDir, 'README.md'), 'utf8')).toMatch(/BRAND\.ELFIS\.2/)
  })

  it('EB22 — contraste tokens', () => {
    expect(BrandColors.textPrimary).toBe('#101828')
    expect(BrandColors.page).toBe('#F5F7FA')
    expect(existsSync(resolve(docsDir, '07-accessibility.md'))).toBe(true)
  })

  it('EB23 — clavier / focus documenté', () => {
    const a11y = readFileSync(resolve(docsDir, '07-accessibility.md'), 'utf8')
    expect(a11y).toMatch(/Focus|clavier/i)
  })

  it('EB24 — zoom 200 % media query', () => {
    const css = readFileSync(membersCss, 'utf8')
    expect(css).toMatch(/@media \(max-width:\s*720px\)/)
  })

  it('EB25 — responsive invite grid', () => {
    const css = readFileSync(membersCss, 'utf8')
    expect(css).toMatch(/grid-template-columns:\s*1fr/)
  })

  it('EB26 — permissions / clés backend inchangées', () => {
    expect(BACKEND_ROLE_TO_GLOBAL).toMatchObject({
      owner: 'owner',
      admin: 'admin',
      cfo: 'manager',
      comptable: 'member',
      employe: 'member',
      auditeur: 'viewer',
    })
  })

  it('EB27 — APIs invite : clés backend préférées', () => {
    const opts = inviteRoleOptions(['admin', 'cfo', 'comptable', 'employe', 'auditeur'])
    expect(opts.map((o) => o.value)).toEqual(['admin', 'cfo', 'employe', 'auditeur'])
    expect(opts.map((o) => o.label)).toEqual([
      'Administrateur',
      'Gestionnaire',
      'Collaborateur',
      'Lecteur',
    ])
  })

  it('EB28 — TypeScript / tokens pilot elfis-core', () => {
    const tokens = buildPilotTokens('elfis-core')
    expect(tokens.primary.toLowerCase()).toBe('#071629')
    expect(tokens.accent.toLowerCase()).toBe('#2764e7')
    expect(tokens.focus.toLowerCase()).toBe('#2764e7')
    expect(SPACE_ACCESS_COLUMN_ENABLED).toBe(false)
  })

  it('EB29 — docs 01–09 présentes', () => {
    for (const name of [
      'README.md',
      '01-runtime-color-audit.md',
      '02-elfis-color-system.md',
      '03-department-accent-rules.md',
      '04-global-role-model.md',
      '05-space-permission-model.md',
      '06-members-page.md',
      '07-accessibility.md',
      '08-test-plan.md',
      '09-implementation-report.md',
    ]) {
      expect(existsSync(resolve(docsDir, name))).toBe(true)
    }
  })

  it('EB30 — footer nav Plateforme (pas ELFIS Core UI) + hors métier', async () => {
    expect(ELFIS_NAV_BRAND.name).toBe('ELFIS')
    expect(ELFIS_NAV_BRAND.subtitle).toBe('Plateforme')
    renderMembers()
    await screen.findByRole('heading', { name: /membres et équipes/i })
    expect(screen.queryByText(/ComptaPilot/i)).toBeNull()
    expect(screen.getByText(/Propriétaire protégé/i)).toBeInTheDocument()
  })
})
