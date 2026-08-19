/**
 * Live preview premium aligné sur le Document Design System (structure PDF).
 * Aperçu HTML — le PDF final reste ReportLab ; même config branding.
 */
import type { ReactNode } from 'react'
import { formatEuro } from '../../../api'
import type {
  CommercialDocType,
  WizardSelectedClient,
  WizardSelectedProduct,
} from '../workflow'
import {
  buildDocumentRenderConfig,
  docTypeTitle,
  partyBlockLabel,
  type DocumentBrandingDraft,
  type OrgDocumentBrandInput,
} from './types'
import './document-design-system.css'

export function DocumentLivingPreview({
  docType,
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
  const config = buildDocumentRenderConfig({ org, branding })
  const title = docTypeTitle(docType)
  const partyLabel = partyBlockLabel(docType)
  const hasClient = Boolean(client?.displayName?.trim())
  const filledProducts = products.filter((p) => p.label.trim())
  const hasProducts = filledProducts.length > 0
  const hasNotes = Boolean(notes.trim())
  const showLogo = config.showLogo && config.hasLogo
  const accentStyle = {
    ['--dds-accent' as string]: config.primaryColor,
    ['--dds-accent-soft' as string]: config.secondaryColor,
  }

  const issuerAside: ReactNode = (
    <div className="dds-preview__issuer">
      {config.addressLines.slice(showLogo ? 0 : 1).map((line) => (
        <p key={line} className="dds-preview__meta">
          {line}
        </p>
      ))}
      {config.contactLines.map((line) => (
        <p key={line} className="dds-preview__meta">
          {line}
        </p>
      ))}
      {config.legalIdLines.slice(0, 2).map((line) => (
        <p key={line} className="dds-preview__meta">
          {line}
        </p>
      ))}
    </div>
  )

  const dateMeta =
    docType === 'devis' ? (
      <p className="dds-preview__meta">Validité : {dueDateLabel}</p>
    ) : docType === 'avoir' ? (
      <p className="dds-preview__meta">Date de référence : {dueDateLabel}</p>
    ) : (
      <p className="dds-preview__meta">
        Échéance : {dueDays} j. · {dueDateLabel}
      </p>
    )

  return (
    <article
      className="dds-preview ds-studio-pdf elf-cmp-preview__sheet"
      data-live-preview="structured"
      data-dds-preview="1"
      data-ds-pdf-skeleton="1"
      data-dds-show-logo={showLogo ? '1' : '0'}
      style={accentStyle}
      aria-label="Aperçu document"
    >
      <header className="dds-preview__header">
        <div className="dds-preview__brand">
          {showLogo ? (
            <img
              className="dds-preview__logo"
              src={config.logoUrl}
              alt=""
              data-dds-brand="logo"
            />
          ) : (
            <p className="dds-preview__org-name" data-dds-brand="name">
              {config.orgNameStrong || 'Entreprise'}
            </p>
          )}
        </div>
        {issuerAside}
      </header>

      <div className="dds-preview__accent" aria-hidden="true" />

      <section className="dds-preview__title-row">
        <div>
          <h3 className="dds-preview__doc-title">{title}</h3>
          <p className="dds-preview__number">
            {docNumber?.trim() ? `N° ${docNumber}` : 'N° —'}
          </p>
        </div>
        <div className="dds-preview__dates">{dateMeta}</div>
      </section>

      <div className="dds-preview__rule" aria-hidden="true" />

      <section
        className="dds-preview__party"
        data-filled={hasClient ? 'true' : 'false'}
        data-dds-block="party"
        data-ds-pdf-block="client"
      >
        <p className="dds-preview__label">{partyLabel}</p>
        {hasClient && client ? (
          <>
            <p className="dds-preview__value">{client.displayName}</p>
            {client.email?.trim() ? (
              <p className="dds-preview__meta">{client.email}</p>
            ) : null}
            {client.address?.trim() ? (
              <p className="dds-preview__meta">{client.address}</p>
            ) : null}
          </>
        ) : (
          <p className="dds-preview__placeholder">Destinataire à sélectionner</p>
        )}
      </section>

      <div className="dds-preview__rule" aria-hidden="true" />

      <section className="dds-preview__lines" data-dds-block="lines" data-ds-pdf-block="lines">
        <table className="dds-preview__table">
          <thead>
            <tr>
              <th>Désignation</th>
              <th>Qté</th>
              <th>PU HT</th>
              <th>Total HT</th>
            </tr>
          </thead>
          <tbody>
            {hasProducts ? (
              filledProducts.map((p, i) => (
                <tr key={p.lineKey ?? `${p.label}-${i}`} data-filled="true">
                  <td>{p.label.trim()}</td>
                  <td>{p.quantity}</td>
                  <td>{formatEuro(p.unitPrice)}</td>
                  <td>{formatEuro(lineTotal(p))}</td>
                </tr>
              ))
            ) : (
              <tr data-skeleton="true">
                <td colSpan={4}>Les lignes apparaîtront ici</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section
        className="dds-preview__totals"
        data-filled={hasProducts ? 'true' : 'false'}
        data-dds-block="totals"
        data-ds-pdf-block="totals"
        aria-live="polite"
      >
        <div>
          <span>Total HT</span>
          <span>{formatEuro(ht)}</span>
        </div>
        {discountTotal > 0 ? (
          <div>
            <span>Remises</span>
            <span>−{formatEuro(discountTotal)}</span>
          </div>
        ) : null}
        <div>
          <span>TVA ({vatRate} %)</span>
          <span>{formatEuro(tva)}</span>
        </div>
        <div className="dds-preview__ttc">
          <strong>Total TTC</strong>
          <strong>{formatEuro(ttc)}</strong>
        </div>
      </section>

      <section
        className="dds-preview__notes"
        data-filled={hasNotes || dueDays >= 0 ? 'true' : 'false'}
        data-dds-block="notes"
        data-ds-pdf-block="terms"
      >
        {hasNotes ? (
          <>
            <p className="dds-preview__label">Notes</p>
            <p className="dds-preview__value">{notes.trim()}</p>
          </>
        ) : null}
        {docType === 'facture' ? (
          <>
            <p className="dds-preview__label">Conditions de paiement</p>
            <p className="dds-preview__meta">
              Échéance : {dueDays} j. · {dueDateLabel}
            </p>
          </>
        ) : null}
        {docType === 'devis' ? (
          <>
            <p className="dds-preview__label">Validité de l’offre</p>
            <p className="dds-preview__meta">Valable jusqu’au {dueDateLabel}</p>
          </>
        ) : null}
      </section>

      <footer className="dds-preview__footer ds-studio-pdf__footer" data-dds-block="legal">
        {config.footerParts.length > 0 ? (
          <p className="dds-preview__legal">{config.footerParts.join(' · ')}</p>
        ) : (
          <p className="dds-preview__placeholder">Mentions légales organisation</p>
        )}
        <span className="dds-preview__page">Page 1</span>
      </footer>
    </article>
  )
}
