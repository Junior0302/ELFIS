import { describe, expect, it, vi, beforeEach } from 'vitest'
import { importApi, importStatusLabel } from '../services/importApi'

describe('import helpers', () => {
  it('libellés statut', () => {
    expect(importStatusLabel('completed')).toMatch(/terminé/i)
    expect(importStatusLabel('rollback_completed')).toMatch(/rollback/i)
  })
})

describe('import API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('liste les documents prêts', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            items: [
              {
                document_id: 'd1',
                validation_session_id: 'v1',
                validation_version: 1,
                status: 'ready_for_import',
                already_imported: false,
              },
            ],
            total: 1,
          }),
      }),
    )
    const res = await importApi.listReady('tok', 1, 'mig-1')
    expect(res.total).toBe(1)
    expect(res.items[0].already_imported).toBe(false)
  })

  it('lance un import', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            id: 'imp-1',
            document_id: 'd1',
            validation_session_id: 'v1',
            validation_version: 1,
            status: 'completed',
            fingerprint: 'abc',
            progress_percent: 100,
            warnings: [],
            created_objects: [{ kind: 'invoice', id: 1 }],
            linked_objects: [],
          }),
      }),
    )
    const run = await importApi.runImport('tok', 1, 'd1')
    expect(run.status).toBe('completed')
    expect(run.created_objects).toHaveLength(1)
  })

  it('n’expose pas de suppression', () => {
    expect(Object.keys(importApi)).not.toContain('delete')
    expect(Object.keys(importApi)).not.toContain('remove')
  })
})
