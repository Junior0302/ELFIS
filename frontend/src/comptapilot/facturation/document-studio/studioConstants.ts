type StudioHeroIcon =
  | 'client'
  | 'items'
  | 'terms'
  | 'notes'
  | 'review'
  | 'finalization'

export const STUDIO_STEP_ICONS: Record<string, StudioHeroIcon> = {
  client: 'client',
  items: 'items',
  terms: 'terms',
  notes_payment: 'notes',
  review: 'review',
  finalization: 'finalization',
}

export const STUDIO_CONSEIL_EXAMPLES: Partial<Record<string, string>> = {
  client:
    'Exemple : un e-mail client renseigné facilite l’envoi du document plus tard.',
  items:
    'Exemple : des libellés clairs aident le destinataire à comprendre la facture.',
  review:
    'Exemple : parcourez les totaux et les contrôles avant de finaliser.',
}
