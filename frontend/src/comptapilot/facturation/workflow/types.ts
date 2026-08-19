/**
 * Workflow officiel documents commerciaux — fondation F1.0.
 * State machine + types ; pas de moteur métier modifié.
 */

export const FACTURATION_WORKFLOW_STEPS = [
  {
    id: 'document-choice',
    label: 'Choix du document',
    description: 'Facture, devis ou avoir',
  },
  {
    id: 'client',
    label: 'Client',
    description: 'Relation / client facturation',
  },
  {
    id: 'products',
    label: 'Produits',
    description: 'Catalogue local',
  },
  {
    id: 'controls',
    label: 'Contrôles',
    description: 'Vérifications dérivées',
  },
  {
    id: 'preview',
    label: 'Prévisualisation',
    description: 'Aperçu du document',
  },
  {
    id: 'validation',
    label: 'Validation',
    description: 'Actions finales',
  },
  {
    id: 'send',
    label: 'Envoi',
    description: 'Étape préparée',
  },
  {
    id: 'archive',
    label: 'Archivage',
    description: 'Étape préparée',
  },
  {
    id: 'accounting',
    label: 'Comptabilisation',
    description: 'Étape préparée',
  },
  {
    id: 'confirmation',
    label: 'Confirmation',
    description: 'Fin du parcours',
  },
] as const

export type FacturationWorkflowStepId = (typeof FACTURATION_WORKFLOW_STEPS)[number]['id']

export type CommercialDocType = 'facture' | 'devis' | 'avoir'

export type CatalogSource = 'local' | 'inventory'

export type WizardSelectedClient = {
  /** ID billing customer (si connu) */
  customerId: number | null
  /** ID SharedRelation (si sélection via Relations) */
  relationId: string | null
  displayName: string
  email: string
  phone?: string
  address?: string
  source: 'billing_customer' | 'shared_relation' | 'manual'
}

export type WizardSelectedProduct = {
  catalogItemId: number | null
  label: string
  quantity: number
  unitPrice: number
  vatRate: number
  /** Remise ligne % — affichage Composer ; appliquée dans draftAmount* locaux */
  discountPercent?: number
  /** Date catalogue réelle si exposée par Resource System — insights « produit récent ». */
  catalogCreatedAt?: string
  /** Clé React stable (F1.3.2.1) — ne pas sérialiser API */
  lineKey?: string
}

export type FacturationWizardDraft = {
  docType: CommercialDocType | null
  client: WizardSelectedClient | null
  products: WizardSelectedProduct[]
  vatRate: number
  notes: string
  dueDays: number
  catalogSource: CatalogSource
  /** Document créé côté API (si brouillon / envoi branché) */
  createdDocId: number | null
  createdDocNumber: string | null
  /** Branding documentaire (showLogo) — source draft / PDF */
  documentBranding: {
    showLogo: boolean
  }
}

export function createEmptyFacturationDraft(
  overrides?: Partial<FacturationWizardDraft>,
): FacturationWizardDraft {
  return {
    docType: null,
    client: null,
    products: [],
    vatRate: 20,
    notes: '',
    dueDays: 30,
    catalogSource: 'local',
    createdDocId: null,
    createdDocNumber: null,
    documentBranding: { showLogo: true },
    ...overrides,
  }
}

export function draftAmountHt(draft: FacturationWizardDraft): number {
  const total = draft.products.reduce((sum, p) => {
    const raw = (Number(p.quantity) || 0) * (Number(p.unitPrice) || 0)
    const discount = Math.min(100, Math.max(0, Number(p.discountPercent) || 0))
    return sum + raw * (1 - discount / 100)
  }, 0)
  return Math.round(total * 100) / 100
}

export function draftAmountTva(draft: FacturationWizardDraft): number {
  const ht = draftAmountHt(draft)
  return Math.round(ht * (Number(draft.vatRate) || 0) * 100) / 10000
}

export function draftAmountTtc(draft: FacturationWizardDraft): number {
  return Math.round((draftAmountHt(draft) + draftAmountTva(draft)) * 100) / 100
}

export function canLeaveFacturationStep(
  stepId: FacturationWorkflowStepId,
  draft: FacturationWizardDraft,
): boolean {
  switch (stepId) {
    case 'document-choice':
      return draft.docType != null
    case 'client':
      return Boolean(draft.client?.displayName?.trim())
    case 'products':
      return draft.products.some((p) => p.label.trim() && (p.quantity > 0 || p.unitPrice >= 0))
    default:
      return true
  }
}

export type DocTypeCard = {
  type: CommercialDocType
  name: string
  description: string
  useCase: string
  icon: 'invoice' | 'quote' | 'credit'
}

export const DOC_TYPE_CARDS: readonly DocTypeCard[] = [
  {
    type: 'facture',
    name: 'Facture',
    description: 'Document fiscal de vente à envoyer au client.',
    useCase: 'Prestations réalisées, biens livrés, échéance de paiement.',
    icon: 'invoice',
  },
  {
    type: 'devis',
    name: 'Devis',
    description: 'Proposition commerciale avant engagement.',
    useCase: 'Chiffrage, négociation, acceptation avant facturation.',
    icon: 'quote',
  },
  {
    type: 'avoir',
    name: 'Avoir',
    description: 'Note de crédit pour corriger ou rembourser.',
    useCase: 'Annulation partielle, retour, ajustement de facture.',
    icon: 'credit',
  },
] as const

/** Résolution source catalogue — InventoryPilot non branché en F1.0. */
export function resolveCatalogSource(inventoryEnabled: boolean): CatalogSource {
  return inventoryEnabled ? 'inventory' : 'local'
}

/** Stub honnête : InventoryPilot n’est pas activé comme source catalogue. */
export function isInventoryCatalogAvailable(): boolean {
  return false
}
