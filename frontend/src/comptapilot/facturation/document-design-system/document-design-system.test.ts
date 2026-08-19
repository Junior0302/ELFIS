/**
 * Document Design System V1 — tests unitaires (DDS01–DDS20 smoke).
 */
import { describe, expect, it } from 'vitest'
import {
  buildDocumentRenderConfig,
  resolveShowLogoDefault,
  isPdfSafeLogoUrl,
  hasAnyLogoUrl,
  partyBlockLabel,
  docTypeTitle,
} from './types'

describe('Document Design System — resolveShowLogoDefault', () => {
  it('DDS01: draft showLogo prioritaire', () => {
    expect(
      resolveShowLogoDefault({
        draftShowLogo: false,
        orgPreference: true,
        hasPdfSafeLogo: true,
      }),
    ).toBe(false)
  })

  it('DDS02: préférence org si pas de draft', () => {
    expect(
      resolveShowLogoDefault({
        draftShowLogo: null,
        orgPreference: false,
        hasPdfSafeLogo: true,
      }),
    ).toBe(false)
  })

  it('DDS03: Avec logo si logo valide et pas de préférence', () => {
    expect(
      resolveShowLogoDefault({
        draftShowLogo: null,
        orgPreference: null,
        hasPdfSafeLogo: true,
      }),
    ).toBe(true)
  })

  it('DDS04: Sans logo si pas de logo', () => {
    expect(
      resolveShowLogoDefault({
        draftShowLogo: null,
        orgPreference: null,
        hasPdfSafeLogo: false,
      }),
    ).toBe(false)
  })
})

describe('Document Design System — logo helpers', () => {
  it('DDS05: SVG non PDF-safe', () => {
    expect(isPdfSafeLogoUrl('/api/org/logos/x.svg')).toBe(false)
  })

  it('DDS06: PNG PDF-safe', () => {
    expect(isPdfSafeLogoUrl('/api/org/logos/x.png')).toBe(true)
  })

  it('DDS07: hasAnyLogoUrl', () => {
    expect(hasAnyLogoUrl('')).toBe(false)
    expect(hasAnyLogoUrl(' /api/org/logos/a.png ')).toBe(true)
  })
})

describe('Document Design System — render config', () => {
  it('DDS08: buildDocumentRenderConfig sans hardcode CreaLab', () => {
    const cfg = buildDocumentRenderConfig({
      org: {
        name: 'Atelier Nord',
        legal_name: 'Atelier Nord SAS',
        logo: '',
        documents_show_logo: null,
        legal_mentions: 'Mentions réelles',
      },
      branding: { showLogo: false },
    })
    expect(cfg.orgNameStrong).toBe('Atelier Nord SAS')
    expect(cfg.showLogo).toBe(false)
    expect(cfg.footerParts.join(' ')).toContain('Mentions réelles')
    expect(JSON.stringify(cfg)).not.toMatch(/CreaLab/i)
    expect(JSON.stringify(cfg)).not.toMatch(/ComptaPilot/i)
  })

  it('DDS09: labels type document', () => {
    expect(docTypeTitle('facture')).toBe('Facture')
    expect(docTypeTitle('devis')).toBe('Devis')
    expect(docTypeTitle('avoir')).toBe('Avoir')
    expect(partyBlockLabel('facture')).toBe('Facturé à')
    expect(partyBlockLabel('devis')).toBe('Destinataire')
    expect(partyBlockLabel('avoir')).toBe('Crédit pour')
  })

  it('DDS10: couleurs org ou défaut', () => {
    const cfg = buildDocumentRenderConfig({
      org: { primary_color: '#123456', secondary_color: '#abcdef' },
      branding: { showLogo: true },
    })
    expect(cfg.primaryColor).toBe('#123456')
    expect(cfg.secondaryColor).toBe('#abcdef')
  })
})
