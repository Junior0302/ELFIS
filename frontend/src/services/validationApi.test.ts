import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  fieldStatusLabel,
  validationApi,
  validationStatusLabel,
} from '../services/validationApi'

describe('validation helpers', () => {
  it('libellés statut', () => {
    expect(validationStatusLabel('ready_for_import')).toMatch(/prêt/i)
    expect(fieldStatusLabel('edited')).toMatch(/modifié/i)
  })
})

describe('validation API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('démarre batch et n’expose pas d’import', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            started: 1,
            errors: [],
            items: [
              {
                id: 'v1',
                document_id: 'd1',
                extraction_id: 'e1',
                status: 'validating',
                validated_data: { document_number: 'FA-1' },
                field_states: {},
                warnings: [],
                errors: [],
                duplicate_summary: { count: 0 },
                matching_summary: { count: 0 },
                progress_percent: 40,
              },
            ],
          }),
      }),
    )
    const res = await validationApi.startSession('tok', 1, 'mig-1')
    expect(res.started).toBe(1)
    expect(JSON.stringify(res)).not.toMatch(/"import_executed":\s*true/)
  })

  it('édite un champ', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            field_path: 'supplier.name',
            ai_value: 'ACME',
            current_value: 'ACME SAS',
            status: 'edited',
            confidence: 0.8,
            provenance: { source: 'user_corrected' },
            warnings: [],
          }),
      }),
    )
    const f = await validationApi.editField('tok', 1, 'v1', 'supplier.name', {
      action: 'edit',
      value: 'ACME SAS',
    })
    expect(f.status).toBe('edited')
    expect(f.provenance.source).toBe('user_corrected')
  })
})
