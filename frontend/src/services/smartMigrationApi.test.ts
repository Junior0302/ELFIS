import { describe, expect, it, vi, beforeEach } from 'vitest'
import { smartMigrationApi } from '../services/smartMigrationApi'

describe('smart migration API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('charge le dashboard', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            data: {
              migration_id: 'm1',
              status: 'running',
              documents_total: 10,
              documents_completed: 4,
              documents_pending: 5,
              documents_failed: 1,
              documents_imported: 3,
              progress_percent: 40,
              throughput_per_min: 1.2,
              avg_duration_ms: 100,
              active_batches: 1,
              active_workers: 2,
              estimated_cost: 0.5,
              actual_cost: 0.4,
              batches: [],
              chart: { labels: ['a'], values: [1] },
            },
          }),
      }),
    )
    const d = await smartMigrationApi.dashboard('tok', 1, 'm1')
    expect(d.progress_percent).toBe(40)
    expect(d.documents_total).toBe(10)
  })

  it('expose resume / cancel / retry', () => {
    expect(typeof smartMigrationApi.resume).toBe('function')
    expect(typeof smartMigrationApi.cancel).toBe('function')
    expect(typeof smartMigrationApi.retryFailed).toBe('function')
  })
})
