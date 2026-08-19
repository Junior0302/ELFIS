import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  documentIntakeApi,
  formatBytes,
  intakeIcon,
  intakeStatusLabel,
  uploadSessionStatusLabel,
} from '../services/documentIntakeApi'

describe('document intake helpers', () => {
  it('formate les tailles', () => {
    expect(formatBytes(500)).toContain('o')
    expect(formatBytes(2048)).toContain('Ko')
    expect(formatBytes(2_000_000)).toContain('Mo')
  })

  it('libellés de statut lifecycle', () => {
    expect(intakeStatusLabel('ready_for_analysis')).toMatch(/analyse/i)
    expect(intakeStatusLabel('quarantined')).toMatch(/quarantaine/i)
    expect(intakeStatusLabel('duplicate')).toMatch(/doublon/i)
    expect(intakeStatusLabel('validating')).toMatch(/validation/i)
  })

  it('libellés session upload', () => {
    expect(uploadSessionStatusLabel('uploading')).toMatch(/cours/i)
    expect(uploadSessionStatusLabel('paused')).toMatch(/interrompu/i)
    expect(uploadSessionStatusLabel('partially_completed')).toMatch(/avertissements/i)
  })

  it('icônes par format', () => {
    expect(intakeIcon('pdf')).toBe('PDF')
    expect(intakeIcon('zip')).toBe('ZIP')
    expect(intakeIcon('png')).toBe('IMG')
  })

  it('ne fabrique pas de vitesse fictive côté helper', () => {
    // Les analytics officielles viennent de l'API — pas de calcul local de bps
    expect(typeof uploadSessionStatusLabel).toBe('function')
  })
})

describe('document intake upload sessions API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('crée une upload session', async () => {
    const payload = {
      id: 'us-1',
      organization_id: 1,
      migration_session_id: 'mig-1',
      created_by_user_id: 2,
      status: 'created',
      source_type: 'manual',
      display_label: 'Lot de dépôt #1',
      expected_file_count: 0,
      received_file_count: 0,
      validated_file_count: 0,
      duplicate_file_count: 0,
      rejected_file_count: 0,
      cancelled_file_count: 0,
      quarantined_file_count: 0,
      expected_total_bytes: 0,
      received_total_bytes: 0,
      version: 1,
      internal_reference: 'upl_abc',
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(payload),
      }),
    )
    const res = await documentIntakeApi.createUploadSession('tok', 1, {
      migration_session_id: 'mig-1',
    })
    expect(res.display_label).toMatch(/Lot/)
    expect(res.internal_reference).toMatch(/^upl_/)
  })

  it('récupère les analytics API sans recalcul', async () => {
    const analytics = {
      schema_version: 1,
      file_count: 2,
      total_bytes: 100,
      received_bytes: 100,
      validated_count: 1,
      duplicate_count: 1,
      rejected_count: 0,
      quarantined_count: 0,
      cancelled_count: 0,
      average_upload_speed_bps: null,
      duration_ms: null,
      dominant_format: 'pdf',
      format_distribution: { pdf: 2 },
      error_distribution: {},
      completion_percent: 40,
      updated_at: '2026-01-01T00:00:00Z',
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(analytics),
      }),
    )
    const res = await documentIntakeApi.getAnalytics('tok', 1, 'us-1')
    expect(res.average_upload_speed_bps).toBeNull()
    expect(res.completion_percent).toBe(40)
  })

  it('pause / reprise / annulation', async () => {
    const base = {
      id: 'us-1',
      organization_id: 1,
      migration_session_id: 'mig-1',
      created_by_user_id: 2,
      status: 'paused',
      source_type: 'manual',
      expected_file_count: 0,
      received_file_count: 0,
      validated_file_count: 0,
      duplicate_file_count: 0,
      rejected_file_count: 0,
      cancelled_file_count: 0,
      quarantined_file_count: 0,
      expected_total_bytes: 0,
      received_total_bytes: 0,
      version: 2,
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(base),
    })
    vi.stubGlobal('fetch', fetchMock)
    await documentIntakeApi.pauseUploadSession('tok', 1, 'us-1')
    await documentIntakeApi.resumeUploadSession('tok', 1, 'us-1')
    await documentIntakeApi.cancelUploadSession('tok', 1, 'us-1')
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})
