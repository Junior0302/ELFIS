/**
 * Mailto composer helpers — personal mailbox mode only.
 * Never use URLSearchParams / application/x-www-form-urlencoded (+ for spaces):
 * Outlook shows literal "+" instead of spaces. Encode each value with encodeURIComponent.
 */

export type MailtoBuildOpts = {
  to: string
  subject: string
  body: string
  cc?: string
  bcc?: string
}

/** Normalize body newlines for mail clients (Outlook prefers CRLF). */
export function mailtoNormalizeNewlines(body: string): string {
  return body.replace(/\r\n/g, '\n').replace(/\n/g, '\r\n')
}

/**
 * Build a mailto: URL. Subject/body/cc/bcc are encodeURIComponent'd individually.
 * Spaces become %20 (never +). Accents, €, apostrophes, em dashes, newlines preserved.
 */
export function buildMailtoUrl(opts: MailtoBuildOpts): string {
  const parts: string[] = []
  if (opts.subject) parts.push(`subject=${encodeURIComponent(opts.subject)}`)
  if (opts.body) {
    parts.push(`body=${encodeURIComponent(mailtoNormalizeNewlines(opts.body))}`)
  }
  if (opts.cc?.trim()) parts.push(`cc=${encodeURIComponent(opts.cc.trim())}`)
  if (opts.bcc?.trim()) parts.push(`bcc=${encodeURIComponent(opts.bcc.trim())}`)
  const qs = parts.join('&')
  // Leave the address unencoded so clients keep a readable path (a@b.com, not a%40b.com).
  return `mailto:${opts.to.trim()}${qs ? `?${qs}` : ''}`
}

/**
 * Soften server default copy that implies an automatic PDF attachment
 * (inappropriate when the client must attach manually).
 */
export function softenMailtoPreviewMessage(message: string): string {
  return (message || '')
    .replace(
      /Veuillez trouver en pièce jointe\s+(notre devis|la facture|notre facture|le devis|l['’]avoir)/gi,
      (_m, kind: string) => `Voici ${kind}`,
    )
    .replace(/\ben pièce jointe\b/gi, 'ci-joint (à ajouter manuellement)')
}

/**
 * Client-facing footnote appended to the mailbox body.
 * Technical mailto limitations stay in the ELFIS UI only — never here.
 */
export function mailtoClientPdfNote(docLabel: string, pdfFilename: string): string {
  const kind =
    docLabel.toLowerCase() === 'devis'
      ? 'le devis'
      : docLabel.toLowerCase() === 'avoir'
        ? "l'avoir"
        : 'la facture'
  return (
    `Le PDF de ${kind} a été téléchargé. Ajoutez-le à ce message avant l'envoi.\n` +
    `Fichier : ${pdfFilename}`
  )
}

export function buildMailtoClientBody(
  message: string,
  docLabel: string,
  pdfFilename: string,
): string {
  const softened = softenMailtoPreviewMessage(message).trim()
  const note = mailtoClientPdfNote(docLabel, pdfFilename)
  if (!softened) return note
  if (softened.includes('Ajoutez-le à ce message')) return softened
  return `${softened}\n\n—\n${note}`
}

/** Open mailto without assigning window.location (avoids navigation / remount side-effects). */
export function openMailtoUrl(url: string): void {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.rel = 'noopener noreferrer'
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

/** Sanitize a download filename for Content-Disposition / <a download>. */
export function sanitizePdfDownloadName(name: string, fallback: string): string {
  const cleaned = (name || '')
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  if (cleaned.toLowerCase().endsWith('.pdf')) return cleaned
  if (cleaned) return `${cleaned}.pdf`
  return fallback.endsWith('.pdf') ? fallback : `${fallback}.pdf`
}
