/**
 * Identité visuelle — étape Vérification (Avec / Sans logo).
 * Choix stocké sur le draft ; préférence org seulement si case cochée + settings.manage.
 */
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { api, type OrgDetail } from '../../../api'
import type { DocumentBrandingDraft } from './types'
import { hasAnyLogoUrl } from './types'
import './document-design-system.css'

const LOGO_ACCEPT = 'image/png,image/jpeg,image/jpg,image/svg+xml,.png,.jpg,.jpeg,.svg'
const MAX_LOGO_BYTES = 2 * 1024 * 1024

export function IdentityVisualSection({
  branding,
  org,
  canEditDoc,
  canManageLogo,
  token,
  orgId,
  onBrandingChange,
  onOrgUpdated,
}: {
  branding: DocumentBrandingDraft
  org: OrgDetail['organization'] | null
  canEditDoc: boolean
  canManageLogo: boolean
  token: string | null
  orgId: number | null
  onBrandingChange: (next: DocumentBrandingDraft, opts?: { persistOrgDefault?: boolean }) => void
  onOrgUpdated: (org: OrgDetail['organization']) => void
}) {
  const groupId = useId()
  const [logoDialogOpen, setLogoDialogOpen] = useState(false)
  const [persistDefault, setPersistDefault] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const hasLogo = hasAnyLogoUrl(org?.logo)
  const showLogo = branding.showLogo

  useEffect(() => {
    if (!logoDialogOpen) setUploadError('')
  }, [logoDialogOpen])

  const setShowLogo = (value: boolean) => {
    if (!canEditDoc) return
    onBrandingChange(
      { ...branding, showLogo: value },
      { persistOrgDefault: persistDefault && canManageLogo },
    )
  }

  const onUpload = async (file: File) => {
    if (!token || orgId == null || !canManageLogo) return
    const lower = file.name.toLowerCase()
    const okType =
      ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml'].includes(file.type) ||
      /\.(png|jpe?g|svg)$/.test(lower)
    if (!okType) {
      setUploadError('Formats acceptés : PNG, JPG, JPEG ou SVG.')
      return
    }
    if (file.size > MAX_LOGO_BYTES) {
      setUploadError('Le logo ne doit pas dépasser 2 Mo.')
      return
    }
    if (lower.endsWith('.svg') || file.type === 'image/svg+xml') {
      // SVG accepté à l’upload ; PDF n’embarque que les miniatures raster.
      // On informe sans bloquer.
    }
    setUploading(true)
    setUploadError('')
    try {
      const res = await api.uploadOrganizationLogo(orgId, file, token)
      onOrgUpdated(res.organization)
      onBrandingChange({ ...branding, showLogo: true })
      setLogoDialogOpen(false)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Échec du téléversement')
    } finally {
      setUploading(false)
    }
  }

  const onFileChange = (e: FormEvent<HTMLInputElement>) => {
    const file = e.currentTarget.files?.[0]
    if (file) void onUpload(file)
    e.currentTarget.value = ''
  }

  return (
    <section
      className="dds-identity"
      data-dds-identity="1"
      aria-labelledby={`${groupId}-title`}
    >
      <h3 id={`${groupId}-title`} className="dds-identity__title">
        Identité visuelle
      </h3>
      <p className="dds-identity__help">
        Affichez ou masquez le logo sur ce document. L’aperçu se met à jour immédiatement.
      </p>

      <div
        className="dds-identity__segment"
        role="radiogroup"
        aria-label="Affichage du logo"
      >
        <label
          className={`dds-identity__option${showLogo ? ' is-active' : ''}${!canEditDoc ? ' is-disabled' : ''}`}
        >
          <input
            type="radio"
            name={`${groupId}-logo`}
            checked={showLogo}
            disabled={!canEditDoc}
            onChange={() => setShowLogo(true)}
          />
          Avec logo
        </label>
        <label
          className={`dds-identity__option${!showLogo ? ' is-active' : ''}${!canEditDoc ? ' is-disabled' : ''}`}
        >
          <input
            type="radio"
            name={`${groupId}-logo`}
            checked={!showLogo}
            disabled={!canEditDoc}
            onChange={() => setShowLogo(false)}
          />
          Sans logo
        </label>
      </div>

      {!hasLogo ? (
        <div className="dds-identity__empty" role="status">
          <p>Aucun logo configuré pour l’organisation.</p>
          <div className="dds-identity__empty-actions">
            {canManageLogo ? (
              <button
                type="button"
                className="btn"
                onClick={() => setLogoDialogOpen(true)}
              >
                Ajouter un logo
              </button>
            ) : (
              <p className="muted">
                Demandez à un administrateur d’ajouter le logo organisation.
              </p>
            )}
            <button
              type="button"
              className="btn secondary"
              disabled={!canEditDoc}
              onClick={() => setShowLogo(false)}
            >
              Continuer sans logo
            </button>
          </div>
        </div>
      ) : null}

      {canManageLogo ? (
        <label className="dds-identity__persist">
          <input
            type="checkbox"
            checked={persistDefault}
            onChange={(e) => {
              const checked = e.target.checked
              setPersistDefault(checked)
              if (checked) {
                onBrandingChange(
                  { ...branding, showLogo },
                  { persistOrgDefault: true },
                )
              }
            }}
          />
          Utiliser ce choix par défaut pour les prochains documents
        </label>
      ) : null}

      {logoDialogOpen ? (
        <div
          className="dds-logo-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby={`${groupId}-logo-dialog`}
        >
          <div className="dds-logo-dialog__panel">
            <h4 id={`${groupId}-logo-dialog`}>Ajouter un logo</h4>
            <p className="muted">
              PNG, JPG ou JPEG recommandés pour le PDF. SVG accepté si une miniature
              peut être générée ; sinon le nom de l’entreprise sera utilisé sur le PDF.
              Taille max. 2 Mo.
            </p>
            <input
              ref={fileRef}
              type="file"
              accept={LOGO_ACCEPT}
              onChange={onFileChange}
              disabled={uploading}
              aria-label="Fichier logo"
            />
            {uploadError ? <p className="error">{uploadError}</p> : null}
            <div className="dds-logo-dialog__actions">
              <button
                type="button"
                className="btn secondary"
                disabled={uploading}
                onClick={() => setLogoDialogOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className="btn"
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
              >
                {uploading ? 'Envoi…' : 'Choisir un fichier'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
