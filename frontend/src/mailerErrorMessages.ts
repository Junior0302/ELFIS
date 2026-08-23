/** Messages FR adaptés — ne jamais tout réduire à « SMTP / Brevo non configuré ». */

export const MAILER_REASON_MESSAGES: Record<string, string> = {
  mailer_disabled: 'L’envoi serveur est désactivé sur cette plateforme.',
  provider_not_configured:
    'Fournisseur d’e-mail non configuré côté serveur ELFIS (SMTP_* ou BREVO_API_KEY).',
  missing_api_key:
    'Clé API Brevo manquante ou invalide (attendu xkeysib-…). Admin : backend .env / Render.',
  missing_smtp_credentials:
    'Identifiants SMTP incomplets (SMTP_HOST, SMTP_USER, SMTP_PASSWORD xsmtpsib-…).',
  sender_not_configured: 'Expéditeur plateforme manquant (PLATFORM_EMAIL_FROM).',
  sender_not_verified: 'L’expéditeur plateforme n’est pas validé chez le fournisseur.',
  provider_unreachable: 'Le fournisseur d’e-mail est injoignable. Réessayez plus tard.',
  authentication_failed:
    'Le service d’envoi ELFIS n’a pas pu s’authentifier auprès du fournisseur de messagerie.',
  attachment_missing: 'Pièce jointe PDF manquante ou non générée.',
  recipient_missing: 'Destinataire manquant.',
  recipient_invalid: 'Adresse e-mail destinataire invalide.',
  delivery_failed: 'Échec de livraison. Aucun message remis au destinataire.',
  timeout: 'Délai dépassé lors de l’envoi.',
  ok: '',
}

export function mailerReasonMessage(code?: string | null): string {
  if (!code || code === 'ok') return ''
  return MAILER_REASON_MESSAGES[code] || MAILER_REASON_MESSAGES.provider_not_configured
}

export type SendButtonState =
  | 'ready'
  | 'config_required'
  | 'missing_recipient'
  | 'mentions_incomplete'
  | 'sending'
  | 'sent'
  | 'failed'
  | 'retry'

export function resolveSendButtonState(opts: {
  canSendDirect: boolean
  recipient: string
  canProceedLegal: boolean
  sending: boolean
  lastFailed: boolean
  lastSent: boolean
}): SendButtonState {
  if (opts.sending) return 'sending'
  if (opts.lastSent) return 'sent'
  if (opts.lastFailed) return 'retry'
  if (!opts.recipient.trim()) return 'missing_recipient'
  if (!opts.canProceedLegal) return 'mentions_incomplete'
  if (!opts.canSendDirect) return 'config_required'
  return 'ready'
}
