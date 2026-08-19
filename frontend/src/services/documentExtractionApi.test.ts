import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  confidenceLabel,
  documentExtractionApi,
  extractionStatusLabel,
  fieldCount,
} from '../services/documentExtractionApi'

describe('document extraction helpers', () => {
  it('libellés statut / confiance / champs', () => {
    expect(extractionStatusLabel('awaiting_human_validation')).toMatch(/validation/i)
    expect(extractionStatusLabel('ocr_pending')).toMatch(/OCR/i)
    expect(confidenceLabel('high')).toMatch(/haute/i)
    expect(fieldCount({ a: 1, supplier: { name: 'ACME' } })).toBeGreaterThan(0)
  })
})

describe('document extraction API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lance extraction session', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            extracted: 1,
            errors: [],
            items: [
              {
                id: 'e1',
                document_id: 'd1',
                universal_document_id: 'DOC-2026-AAAAAAAA',
                schema_name: 'invoice.v1',
                schema_version: '1.0.0',
                extraction_version: '1.0.0',
                status: 'awaiting_human_validation',
                strategy: 'heuristic',
                overall_confidence: 0.82,
                confidence_level: 'medium',
                requires_human_review: true,
                structured_data: { document_number: 'FA-1', amounts: { total_including_tax: 120 } },
                warnings: [],
                errors: [],
                progress_percent: 100,
              },
            ],
          }),
      }),
    )
    const res = await documentExtractionApi.extractSession('tok', 1, 'mig-1')
    expect(res.extracted).toBe(1)
    expect(res.items[0].requires_human_review).toBe(true)
    expect(res.items[0].status).toBe('awaiting_human_validation')
    expect(JSON.stringify(res)).not.toMatch(/system prompt/i)
  })

  it('liste et relance', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ items: [], total: 0 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            id: 'e1',
            document_id: 'd1',
            schema_name: 'invoice.v1',
            schema_version: '1.0.0',
            extraction_version: '1.0.0',
            status: 'awaiting_human_validation',
            requires_human_review: true,
            structured_data: {},
            warnings: [],
            errors: [],
            progress_percent: 100,
          }),
      })
    vi.stubGlobal('fetch', fetchMock)
    await documentExtractionApi.listExtractions('tok', 1, 'mig-1')
    await documentExtractionApi.retry('tok', 1, 'e1')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
