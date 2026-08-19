import { createElement } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import MigrationExtractionPanel from '../components/MigrationExtractionPanel'

describe('MigrationExtractionPanel lecture seule', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify({ items: [], total: 0 }),
      }),
    )
  })

  it('n’expose ni bouton import ni édition ni choix provider/modèle', () => {
    const html = renderToStaticMarkup(
      createElement(MigrationExtractionPanel, {
        token: 'tok',
        orgId: 1,
        migrationSessionId: 'mig-1',
      }),
    )
    expect(html).toMatch(/Extraction IA/i)
    expect(html).not.toMatch(/>\s*Importer\s*</i)
    expect(html).not.toMatch(/>\s*Éditer\s*</i)
    expect(html).not.toMatch(/type="text"/i)
    expect(html).not.toMatch(/<textarea/i)
    expect(html).not.toMatch(/name="provider"/i)
    expect(html).not.toMatch(/name="model"/i)
    expect(html).toMatch(/Lancer/i)
    expect(html).toMatch(/Aucun import|validation humaine/i)
  })
})
