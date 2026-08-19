import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  classificationLabel,
  documentAnalysisApi,
  languageLabel,
  warningLabel,
} from '../services/documentAnalysisApi'

describe('document analysis helpers', () => {
  it('libellés classification / langue / warnings', () => {
    expect(classificationLabel('invoice')).toMatch(/facture/i)
    expect(languageLabel('fr')).toMatch(/français/i)
    expect(warningLabel('ocr_recommended')).toMatch(/OCR/i)
  })
})

describe('document analysis API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lance analyse session', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            analyzed: 1,
            errors: [],
            items: [
              {
                id: 'r1',
                organization_id: 1,
                document_intake_item_id: 'i1',
                status: 'completed',
                schema_version: 1,
                analysis_version: '1.0.0',
                need_ocr: false,
                classification_label: 'invoice',
                language_code: 'fr',
                quality_score: 80,
                orientation_degrees: 0,
                warnings: [],
                steps_completed: 12,
                steps_total: 12,
                progress_percent: 100,
                report: { llm_used: false, ocr_executed: false },
              },
            ],
          }),
      }),
    )
    const res = await documentAnalysisApi.analyzeSession('tok', 1, 'mig-1')
    expect(res.analyzed).toBe(1)
    expect(res.items[0].need_ocr).toBe(false)
    expect(res.items[0].report.llm_used).toBe(false)
  })
})
