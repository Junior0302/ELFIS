export const FICTIONAL_BANK_LABEL = 'Banque Démo ELFIS — données fictives'

export function isFictionalBankProvider(provider: string | undefined | null): boolean {
  return provider === 'demo'
}

export function providerPublicLabel(input: {
  provider: string
  display_name: string
  status: string
  fictional?: boolean
}): string {
  if (input.fictional || isFictionalBankProvider(input.provider)) {
    return FICTIONAL_BANK_LABEL
  }
  if (input.status === 'not_configured') {
    return `${input.display_name} — configuration requise`
  }
  return input.display_name
}
