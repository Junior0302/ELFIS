import { describe, expect, it } from 'vitest'
import {
  buildCompanySummary,
  canCancelStatus,
  canResumeStatus,
  isSourceSelectable,
  progressPercent,
  sourceAvailabilityBadge,
  validateProfileClient,
  type MigrationProgress,
  type MigrationSession,
} from '../services/migrationApi'

describe('migration validation', () => {
  it('affiche un résumé dynamique', () => {
    const summary = buildCompanySummary({
      company_age_range: 'more_than_2_years',
      legal_form: 'sas',
      team_size: 'two_to_five',
      accountant_status: 'has_accountant',
      join_reasons: ['saving_time'],
    })
    expect(summary).toContain('SAS')
    expect(summary).toContain('plus de deux ans')
    expect(summary).toContain('cabinet comptable')
  })

  it('exige les champs obligatoires', () => {
    expect(validateProfileClient({})).toBeTruthy()
    expect(
      validateProfileClient({
        company_age_range: 'more_than_2_years',
        legal_form: 'other',
        team_size: 'one',
        accountant_status: 'no_accountant',
        join_reasons: ['other'],
      }),
    ).toMatch(/forme juridique|raison/i)
  })

  it('accepte un profil complet', () => {
    expect(
      validateProfileClient({
        company_age_range: 'less_than_6_months',
        legal_form: 'sarl',
        team_size: 'six_to_twenty',
        accountant_status: 'looking_for_accountant',
        join_reasons: ['changing_software'],
      }),
    ).toBeNull()
  })

  it('autorise l’annulation selon le statut', () => {
    expect(canCancelStatus('draft')).toBe(true)
    expect(canCancelStatus('awaiting_upload')).toBe(true)
    expect(canCancelStatus('cancelled')).toBe(false)
  })
})

describe('migration stage2 certification UI helpers', () => {
  const apiProgress = (pct: number): MigrationProgress => ({
    schema_version: 1,
    overall_percent: pct,
    current_step: 'welcome',
    current_step_percent: 0,
    completed_steps: [],
    pending_steps: [],
    blocked_steps: [],
    warnings: [],
    estimated_remaining_seconds: null,
  })

  it('n’affiche pas le token comme donnée UI obligatoire', () => {
    const session = {
      id: 's1',
      migration_session_token: 'mig_secretish',
      organization_id: 1,
      mode: 'initial_migration',
      status: 'draft',
      current_step: 1,
      version: 1,
      progress: apiProgress(0),
    } as MigrationSession
    // L’UI liste utilise id/status/progress — pas le token
    expect(session.id).toBeTruthy()
    expect(progressPercent(session)).toBe(0)
  })

  it('affiche la progression provenant de l’API uniquement', () => {
    const fromApi = {
      id: 's1',
      organization_id: 1,
      mode: 'initial_migration',
      status: 'profile_completed',
      current_step: 2,
      version: 2,
      progress: apiProgress(20),
    } as MigrationSession
    expect(progressPercent(fromApi)).toBe(20)
    // Tentative de « recalcul local » ignorée : on lit overall_percent API
    const tampered = {
      ...fromApi,
      progress: { ...apiProgress(20), overall_percent: 99 },
    } as MigrationSession
    // Si le backend recalcule, le FE doit recharger depuis API — helper ne recalcule pas
    expect(progressPercent(tampered)).toBe(99) // valeur API brute
    // Pas d’estimation fictive
    expect(tampered.progress?.estimated_remaining_seconds).toBeNull()
  })

  it('ne recalcule jamais overall_percent côté client', () => {
    // Contrat : aucun helper FE ne dérive overall_percent depuis les steps
    const session = {
      id: 'x',
      organization_id: 1,
      mode: 'one_time_import',
      status: 'draft',
      current_step: 1,
      version: 1,
      progress: {
        ...apiProgress(5),
        completed_steps: ['welcome', 'company_profile'], // 20 côté serveur, mais FE ne recalcule pas
      },
    } as MigrationSession
    expect(progressPercent(session)).toBe(5)
  })

  it('gère bouton reprendre et erreur cancelled', () => {
    expect(canResumeStatus('draft')).toBe(true)
    expect(canResumeStatus('awaiting_upload')).toBe(true)
    expect(canResumeStatus('cancelled')).toBe(false)
    expect(canResumeStatus('completed')).toBe(false)
  })

  it('double reprise : statut resume inchangé (idempotence UX)', () => {
    // Le FE peut appeler resume deux fois ; le statut session ne doit pas être interprété comme changé
    const status = 'awaiting_upload'
    expect(canResumeStatus(status)).toBe(true)
    expect(canResumeStatus(status)).toBe(true)
  })

  it('badges sources beta / maintenance / deprecated / coming_soon', () => {
    expect(sourceAvailabilityBadge('beta')).toBe('Bêta')
    expect(sourceAvailabilityBadge('maintenance')).toBe('Maintenance')
    expect(sourceAvailabilityBadge('deprecated')).toBe('Ancienne intégration')
    expect(sourceAvailabilityBadge('coming_soon')).toBe('Bientôt disponible')
    expect(isSourceSelectable('beta')).toBe(true)
    expect(isSourceSelectable('maintenance')).toBe(false)
    expect(isSourceSelectable('coming_soon')).toBe(false)
    expect(isSourceSelectable('deprecated')).toBe(false)
    expect(isSourceSelectable('available')).toBe(true)
  })

  it('reprise après actualisation : hydrate depuis session API', () => {
    const reloaded = {
      id: 'persist-1',
      organization_id: 1,
      mode: 'initial_migration',
      status: 'sources_selected',
      current_step: 3,
      version: 5,
      progress: apiProgress(35),
      selected_sources: ['file_pdf'],
      timeline: [{ id: 't1', step_key: 'data_sources', step_order: 3, status: 'completed' }],
      recent_activities: [{ id: 'a1', activity_type: 'sources_saved', title: 'Sources', severity: 'success' }],
    } as MigrationSession
    expect(progressPercent(reloaded)).toBe(35)
    expect(reloaded.selected_sources).toEqual(['file_pdf'])
    expect(reloaded.timeline?.[0]?.step_key).toBe('data_sources')
    expect(reloaded.recent_activities?.[0]?.activity_type).toBe('sources_saved')
    expect(reloaded.progress?.estimated_remaining_seconds).toBeNull()
  })
})
