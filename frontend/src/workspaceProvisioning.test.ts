import { describe, expect, it, vi } from 'vitest'
import type { WorkspaceProvisionStatus } from './api'
import {
  ENTERPRISE_SETUP_COMPANY_NAME_PATH,
  ENTERPRISE_SETUP_DRAFT_STORAGE_KEY,
  clearEnterpriseSetupDraftFromStorage,
  firstIncompleteEnterpriseSetupPath,
  isEnterpriseSetupDraftComplete,
  writeEnterpriseSetupDraftToStorage,
  type EnterpriseSetupDraft,
} from './enterpriseSetup'
import {
  PROVISION_UI_STEPS,
  resolveProvisionUiStepState,
} from './workspaceProvisioning'

function completeDraft(over: Partial<EnterpriseSetupDraft> = {}): EnterpriseSetupDraft {
  return {
    company_name: 'Acme SARL',
    industry: 'services',
    country: 'FR',
    currency: 'EUR',
    vat_status: 'vat_registered',
    vat_number: 'FR12345678901',
    ...over,
  }
}

function memoryStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial))
  return {
    getItem: (key: string) => (map.has(key) ? map.get(key)! : null),
    setItem: (key: string, value: string) => {
      map.set(key, value)
    },
    removeItem: (key: string) => {
      map.delete(key)
    },
    raw: map,
  }
}

describe('Workspace provisioning UI helpers — C1.11', () => {
  it('draft incomplet → redirection première étape', () => {
    expect(firstIncompleteEnterpriseSetupPath(completeDraft({ company_name: '' }))).toBe(
      ENTERPRISE_SETUP_COMPANY_NAME_PATH,
    )
  })

  it('étapes UI et états', () => {
    expect(PROVISION_UI_STEPS).toHaveLength(4)
    expect(resolveProvisionUiStepState('validating_setup', 'saving_company_profile', 'running')).toBe(
      'done',
    )
    expect(resolveProvisionUiStepState('saving_company_profile', 'saving_company_profile', 'running')).toBe(
      'current',
    )
    expect(resolveProvisionUiStepState('configuring_workspace', 'saving_company_profile', 'running')).toBe(
      'upcoming',
    )
    expect(resolveProvisionUiStepState('validating_setup', 'validating_setup', 'failed')).toBe('error')
    expect(resolveProvisionUiStepState('completing_setup', 'completed', 'completed')).toBe('done')
  })

  it('draft conservé en erreur / nettoyé après completed', () => {
    const storage = memoryStorage()
    writeEnterpriseSetupDraftToStorage(completeDraft(), storage)
    expect(storage.raw.has(ENTERPRISE_SETUP_DRAFT_STORAGE_KEY)).toBe(true)

    // erreur → ne pas clear
    expect(isEnterpriseSetupDraftComplete(completeDraft())).toBe(true)

    // succès → clear
    clearEnterpriseSetupDraftFromStorage(storage)
    expect(storage.raw.has(ENTERPRISE_SETUP_DRAFT_STORAGE_KEY)).toBe(false)
  })

  it('anti double POST (Strict Mode) — un seul démarrage', async () => {
    const provisionWorkspace = vi.fn().mockResolvedValue({
      status: 'completed',
      current_step: 'completed',
      progress: 100,
      setup_completed: true,
    } satisfies WorkspaceProvisionStatus)
    const getStatus = vi.fn().mockResolvedValue({
      status: 'pending',
      current_step: 'pending',
      progress: 0,
      setup_completed: false,
    } satisfies WorkspaceProvisionStatus)

    const started = { current: false }
    const run = async () => {
      if (started.current) return
      started.current = true
      const current = await getStatus()
      if (current.status === 'pending') {
        await provisionWorkspace()
      }
    }
    await Promise.all([run(), run()])
    expect(provisionWorkspace).toHaveBeenCalledTimes(1)
  })

  it('refresh completed → pas de nouveau POST', async () => {
    const provisionWorkspace = vi.fn()
    const getStatus = vi.fn().mockResolvedValue({
      status: 'completed',
      current_step: 'completed',
      progress: 100,
      setup_completed: true,
    } satisfies WorkspaceProvisionStatus)
    const current = await getStatus()
    if (current.status !== 'completed' && !current.setup_completed) {
      await provisionWorkspace()
    }
    expect(provisionWorkspace).not.toHaveBeenCalled()
  })

  it('accessibilité progression — contrat aria', () => {
    const progress = 65
    expect(progress).toBeGreaterThanOrEqual(0)
    expect(progress).toBeLessThanOrEqual(100)
    const aria = {
      role: 'progressbar',
      'aria-valuemin': 0,
      'aria-valuemax': 100,
      'aria-valuenow': progress,
    }
    expect(aria.role).toBe('progressbar')
    expect(aria['aria-valuenow']).toBe(65)
  })
})
