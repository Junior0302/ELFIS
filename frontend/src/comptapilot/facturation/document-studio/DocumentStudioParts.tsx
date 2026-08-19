/**
 * Document Studio V1 — presentation helpers (F1.3.5)
 * UI only: heroes, PDF skeleton, smart cards, conseil placeholder.
 * No API / workflow / accounting logic.
 */
import type { ReactNode, RefObject } from 'react'
import { formatEuro } from '../../../api'
import {
  DocumentLivingPreview,
  type DocumentBrandingDraft,
  type OrgDocumentBrandInput,
} from '../document-design-system'
import type {
  CommercialDocType,
  WizardSelectedClient,
  WizardSelectedProduct,
} from '../workflow'
import './document-studio.css'

export type StudioHeroIcon =
  | 'client'
  | 'items'
  | 'terms'
  | 'notes'
  | 'review'
  | 'finalization'

const HERO_PATHS: Record<StudioHeroIcon, ReactNode> = {
  client: (
    <path
      d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-3.3 0-6 1.7-6 3.8V20h12v-2.2C18 15.7 15.3 14 12 14Z"
      fill="currentColor"
    />
  ),
  items: (
    <path
      d="M4 6h16v2H4V6Zm0 5h16v2H4v-2Zm0 5h10v2H4v-2Z"
      fill="currentColor"
    />
  ),
  terms: (
    <path
      d="M7 3h10a2 2 0 0 1 2 2v14l-7-3-7 3V5a2 2 0 0 1 2-2Zm0 2v11.1l5-2.1 5 2.1V5H7Z"
      fill="currentColor"
    />
  ),
  notes: (
    <path
      d="M5 4h14v16H5V4Zm2 2v12h10V6H7Zm2 2h6v2H9V8Zm0 4h6v2H9v-2Z"
      fill="currentColor"
    />
  ),
  review: (
    <path
      d="M9.5 16.2 5.8 12.5l1.4-1.4 2.3 2.3 6.3-6.3 1.4 1.4-7.7 7.7Z"
      fill="currentColor"
    />
  ),
  finalization: (
    <path
      d="M12 3 4 7v5c0 4.4 3.2 8.4 8 9.5 4.8-1.1 8-5.1 8-9.5V7l-8-4Zm0 2.2 6 3v4.3c0 3.3-2.3 6.3-6 7.3-3.7-1-6-4-6-7.3V8.2l6-3Z"
      fill="currentColor"
    />
  ),
}

export function StudioStepHero({
  title,
  help,
  icon,
  headingRef,
  headingId = 'fp-guided-step-heading',
}: {
  title: string
  help: string
  icon: StudioHeroIcon
  headingRef?: RefObject<HTMLHeadingElement | null>
  headingId?: string
}) {
  return (
    <header className="ds-studio-hero" data-ds-studio-hero={icon}>
      <span className="ds-studio-hero__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          {HERO_PATHS[icon]}
        </svg>
      </span>
      <div>
        <h2
          id={headingId}
          ref={headingRef}
          className="ds-studio-hero__title"
          tabIndex={-1}
        >
          {title}
        </h2>
        <p className="ds-studio-hero__help">{help}</p>
      </div>
    </header>
  )
}

/** Smart client card — real draft fields only; omit empty metas (no invented scores). */
export function StudioClientSmartCard({ client }: { client: WizardSelectedClient }) {
  const metas: { key: string; label: string; value: string }[] = []
  if (client.email?.trim()) metas.push({ key: 'email', label: 'E-mail', value: client.email.trim() })
  if (client.phone?.trim()) metas.push({ key: 'phone', label: 'Tél.', value: client.phone.trim() })
  if (client.address?.trim())
    metas.push({ key: 'address', label: 'Adresse', value: client.address.trim() })

  return (
    <div
      className="ds-studio-card ds-studio-card--smart fp-composer-client-card"
      role="status"
      data-ds-smart-card="client"
    >
      <p className="ds-studio-card__name">{client.displayName}</p>
      {metas.length > 0 ? (
        <ul className="ds-studio-card__meta">
          {metas.map((m) => (
            <li key={m.key}>
              {m.label} : {m.value}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

/** Products summary — only real line labels / amounts; omit if empty. */
export function StudioProductsSmartCard({
  products,
  lineTotal,
}: {
  products: WizardSelectedProduct[]
  lineTotal: (p: WizardSelectedProduct) => number
}) {
  const filled = products.filter((p) => p.label.trim())
  if (filled.length === 0) return null

  return (
    <div
      className="ds-studio-card ds-studio-card--smart"
      role="status"
      data-ds-smart-card="products"
    >
      <p className="ds-studio-card__name">
        {filled.length} ligne{filled.length > 1 ? 's' : ''} sélectionnée
        {filled.length > 1 ? 's' : ''}
      </p>
      <div className="ds-studio-products-summary">
        {filled.slice(0, 4).map((p, i) => (
          <div
            key={p.lineKey ?? `${p.label}-${i}`}
            className="ds-studio-products-summary__row"
          >
            <span>
              {p.label.trim()}
              <span className="ds-studio-products-summary__secondary">
                {' '}
                · {p.quantity} × {formatEuro(p.unitPrice)}
              </span>
            </span>
            <strong>{formatEuro(lineTotal(p))}</strong>
          </div>
        ))}
        {filled.length > 4 ? (
          <p className="ds-studio-products-summary__secondary">
            + {filled.length - 4} autre{filled.length - 4 > 1 ? 's' : ''}
          </p>
        ) : null}
      </div>
    </div>
  )
}

/**
 * Conseil ComptaPilot — UI placeholder only.
 * Examples are illustrative; never presented as computed facts.
 */
export function StudioConseilPlaceholder({
  example,
}: {
  example: string
}) {
  return (
    <aside
      className="ds-studio-conseil"
      data-ds-conseil="placeholder"
      aria-label="Conseil ComptaPilot (exemple illustratif)"
    >
      <p className="ds-studio-conseil__label">Conseil ComptaPilot</p>
      <p className="ds-studio-conseil__example">{example}</p>
      <p className="ds-studio-conseil__disclaimer">
        Exemple d’interface — moteur IA non connecté. Aucune affirmation métier.
      </p>
    </aside>
  )
}

export function StudioLivingPdf({
  docType,
  docTypeLabel: _docTypeLabel,
  client,
  products,
  notes,
  dueDays,
  dueDateLabel,
  vatRate,
  ht,
  tva,
  ttc,
  discountTotal,
  docNumber,
  lineTotal,
  org,
  branding,
}: {
  docType: CommercialDocType | null
  docTypeLabel?: string
  client: WizardSelectedClient | null
  products: WizardSelectedProduct[]
  notes: string
  dueDays: number
  dueDateLabel: string
  vatRate: number
  ht: number
  tva: number
  ttc: number
  discountTotal: number
  docNumber: string | null
  lineTotal: (p: WizardSelectedProduct) => number
  org?: OrgDocumentBrandInput | null
  branding?: DocumentBrandingDraft | null
}) {
  return (
    <DocumentLivingPreview
      docType={docType}
      client={client}
      products={products}
      notes={notes}
      dueDays={dueDays}
      dueDateLabel={dueDateLabel}
      vatRate={vatRate}
      ht={ht}
      tva={tva}
      ttc={ttc}
      discountTotal={discountTotal}
      docNumber={docNumber}
      lineTotal={lineTotal}
      org={org}
      branding={branding}
    />
  )
}

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
