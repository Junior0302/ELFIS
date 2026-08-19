import { describe, expect, it } from 'vitest'
import { mailerReasonMessage, resolveSendButtonState } from './mailerErrorMessages'

describe('mailerErrorMessages', () => {
  it('maps reason codes to distinct FR messages', () => {
    expect(mailerReasonMessage('missing_smtp_credentials')).toMatch(/SMTP/)
    expect(mailerReasonMessage('missing_api_key')).toMatch(/API Brevo/)
    expect(mailerReasonMessage('provider_not_configured')).not.toBe(
      mailerReasonMessage('authentication_failed'),
    )
    expect(mailerReasonMessage('ok')).toBe('')
  })

  it('resolves send button states', () => {
    expect(
      resolveSendButtonState({
        canSendDirect: true,
        recipient: 'a@b.fr',
        canProceedLegal: true,
        sending: false,
        lastFailed: false,
        lastSent: false,
      }),
    ).toBe('ready')
    expect(
      resolveSendButtonState({
        canSendDirect: false,
        recipient: 'a@b.fr',
        canProceedLegal: true,
        sending: false,
        lastFailed: false,
        lastSent: false,
      }),
    ).toBe('config_required')
    expect(
      resolveSendButtonState({
        canSendDirect: true,
        recipient: '',
        canProceedLegal: true,
        sending: false,
        lastFailed: false,
        lastSent: false,
      }),
    ).toBe('missing_recipient')
  })
})
