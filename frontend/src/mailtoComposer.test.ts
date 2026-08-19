import { describe, expect, it } from 'vitest'
import {
  buildMailtoClientBody,
  buildMailtoUrl,
  mailtoClientPdfNote,
  mailtoNormalizeNewlines,
  sanitizePdfDownloadName,
  softenMailtoPreviewMessage,
} from './mailtoComposer'

describe('mailtoComposer — encoding', () => {
  it('encode les espaces en %20, jamais en +', () => {
    const url = buildMailtoUrl({
      to: 'client@exemple.fr',
      subject: 'Facture FAC-2026-0001 — Crealab Auto',
      body: 'Bonjour le monde',
    })
    expect(url).not.toMatch(/\+/)
    expect(url).toContain('subject=Facture%20FAC-2026-0001')
    expect(url).toContain('%E2%80%94') // em dash —
    expect(url).toContain('body=Bonjour%20le%20monde')
  })

  it('préserve accents, apostrophes, € et tiret long dans subject/body', () => {
    const subject = "Facture FAC-2026-0001 — L'été Crealab Auto"
    const body = "Montant : 1 200 €\nMerci d'avance"
    const url = buildMailtoUrl({ to: 'a@b.c', subject, body })
    expect(url).not.toMatch(/\+/)
    const subjectPart = url.split('subject=')[1]?.split('&')[0] || ''
    const bodyPart = url.split('body=')[1] || ''
    expect(decodeURIComponent(subjectPart)).toBe(subject)
    expect(decodeURIComponent(bodyPart)).toBe(mailtoNormalizeNewlines(body))
    expect(decodeURIComponent(bodyPart)).toContain('€')
    expect(decodeURIComponent(bodyPart)).toContain("d'avance")
  })

  it('encode subject et body séparément (pas toute l’URL)', () => {
    const url = buildMailtoUrl({
      to: 'client@exemple.fr',
      subject: 'Objet',
      body: 'Corps',
    })
    expect(url.startsWith('mailto:client@exemple.fr?')).toBe(true)
    expect(url).not.toContain(encodeURIComponent('mailto:'))
  })

  it('normalise les newlines en CRLF pour Outlook', () => {
    expect(mailtoNormalizeNewlines('a\nb\nc')).toBe('a\r\nb\r\nc')
    expect(mailtoNormalizeNewlines('a\r\nb')).toBe('a\r\nb')
  })

  it('n’utilise pas URLSearchParams (régression +)', () => {
    // URLSearchParams would produce subject=Hello+World
    const viaParams = new URLSearchParams({ subject: 'Hello World' }).toString()
    expect(viaParams).toContain('+')
    const viaMailto = buildMailtoUrl({ to: 'x@y.z', subject: 'Hello World', body: '' })
    expect(viaMailto).toContain('%20')
    expect(viaMailto).not.toContain('+')
  })
})

describe('mailtoComposer — client body', () => {
  it('adoucit « Veuillez trouver en pièce jointe »', () => {
    const raw =
      'Bonjour Client,\n\nVeuillez trouver en pièce jointe la facture FAC-1 d’un montant de 10,00 €.\n\nCordialement,'
    const soft = softenMailtoPreviewMessage(raw)
    expect(soft).not.toMatch(/Veuillez trouver en pièce jointe/i)
    expect(soft).toContain('Voici la facture')
  })

  it('note client claire sans jargon mailto technique', () => {
    const note = mailtoClientPdfNote('Facture', 'Facture-FAC-2026-0001-Crealab-Auto.pdf')
    expect(note).toContain('Le PDF de la facture a été téléchargé')
    expect(note).toContain('Ajoutez-le à ce message')
    expect(note).not.toMatch(/mailto/i)
    expect(note).not.toMatch(/automatiquement/i)
  })

  it('compose le corps mailto sans note technique', () => {
    const body = buildMailtoClientBody(
      'Veuillez trouver en pièce jointe la facture FAC-1.',
      'Facture',
      'Facture-FAC-1-Org.pdf',
    )
    expect(body).not.toMatch(/mailto/i)
    expect(body).toContain('Ajoutez-le à ce message')
    expect(body).toContain('Facture-FAC-1-Org.pdf')
  })
})

describe('mailtoComposer — filename', () => {
  it('sanitize un nom PDF lisible', () => {
    expect(sanitizePdfDownloadName('Facture-FAC-2026-0001-Crealab-Auto.pdf', 'x.pdf')).toBe(
      'Facture-FAC-2026-0001-Crealab-Auto.pdf',
    )
    expect(sanitizePdfDownloadName('Facture FAC 1 / Org', 'fallback.pdf')).toBe(
      'Facture-FAC-1-Org.pdf',
    )
  })
})
