import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, formatEuro } from '../../api'
import { useAuth } from '../../auth'
import {
  CustomerPicker,
  ProductPicker,
  catalogResultToLineFields,
  type SearchResult,
} from '../../platform-search'
import {
  createEmptyFacturationDraft,
  deriveWizardControls,
  DOC_TYPE_CARDS,
  isInventoryCatalogAvailable,
  COMPOSER_GUIDED_STEPS,
  deriveGuidedStepStatuses,
  getComposerStepMeta,
  guidedProgressPercent,
  isComposerStep,
  nextComposerStep,
  prevComposerStep,
  validateComposerStep,
  type CommercialDocType,
  type ComposerStep,
  type FacturationWizardDraft,
  type WizardSelectedClient,
  type WizardSelectedProduct,
} from '../../comptapilot/facturation/workflow'
import {
  deriveLiveDocumentInsights,
  deriveLiveDocumentStatus,
  LiveInsightsPanel,
  LiveTotals,
  snapshotLiveTotals,
} from '../../comptapilot/facturation/live-document'
import { LibraryCatalogModal } from '../../comptapilot/facturation/LibraryCatalogModal'
import { ExitConfirmationDialog } from '../../comptapilot/facturation/ExitConfirmationDialog'
import {
  StudioConseilPlaceholder,
  StudioClientSmartCard,
  StudioLivingPdf,
  StudioProductsSmartCard,
  StudioStepHero,
  STUDIO_CONSEIL_EXAMPLES,
  STUDIO_STEP_ICONS,
} from '../../comptapilot/facturation/document-studio'
import {
  IdentityVisualSection,
  resolveShowLogoDefault,
  hasAnyLogoUrl,
  type OrgDocumentBrandInput,
} from '../../comptapilot/facturation/document-design-system'
import type { OrgDetail } from '../../api'
import '../../comptapilot/facturation/facturation-spaces.css'
import '../../comptapilot/facturation/live-document/live-document.css'
import '../../comptapilot/facturation/document-studio/document-studio.css'
import '../../comptapilot/facturation/document-design-system/document-design-system.css'
import {
  ComposerFocusLayout,
  ComposerPreview,
  ComposerSection,
  ComposerValidation,
  useComposerFocus,
  type ComposerActionDef,
  type ComposerAutosaveState,
  type ComposerDefinition,
  type ComposerPreviewState,
  type ComposerStepDefinition,
  type ComposerStepStatus,
  type ComposerValidationIssue,
} from '../../composer-framework'

const COMPOSER_PROGRESS_STEPS: readonly ComposerStepDefinition[] = [
  { id: 'type', label: 'Type' },
  { id: 'client', label: 'Client' },
  { id: 'lines', label: 'Lignes' },
  { id: 'required', label: 'Champs' },
  { id: 'controls', label: 'Contrôles' },
]

const GUIDED_PROGRESS_STEPS: readonly ComposerStepDefinition[] = COMPOSER_GUIDED_STEPS.map(
  (s) => ({ id: s.id, label: s.label }),
)

function parseDocType(raw: string | null): CommercialDocType | null {
  if (raw === 'facture' || raw === 'devis' || raw === 'avoir') return raw
  return null
}

function composerTitle(docType: CommercialDocType | null): string {
  if (docType === 'facture') return 'Nouvelle facture'
  if (docType === 'devis') return 'Nouveau devis'
  if (docType === 'avoir') return 'Nouvel avoir'
  return 'Nouveau document'
}

function mapControls(issues: ReturnType<typeof deriveWizardControls>): ComposerValidationIssue[] {
  return issues.map((i) => ({
    id: i.id,
    severity: i.severity,
    message: i.message,
    field: i.field,
  }))
}

function lineTotal(line: WizardSelectedProduct): number {
  const discount = Math.min(100, Math.max(0, Number(line.discountPercent) || 0))
  const raw = (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0)
  return Math.round(raw * (1 - discount / 100) * 100) / 100
}

function createLineKey(): string {
  return `ln-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
}

function blankLine(vatRate: number): WizardSelectedProduct {
  return {
    catalogItemId: null,
    label: '',
    quantity: 1,
    unitPrice: 0,
    vatRate,
    discountPercent: 0,
    lineKey: createLineKey(),
  }
}

function withLineKey(line: WizardSelectedProduct): WizardSelectedProduct {
  return line.lineKey ? line : { ...line, lineKey: createLineKey() }
}

function deriveProgress(
  draft: FacturationWizardDraft,
  blockingErrors: number,
): {
  currentStepId: string
  stepStatuses: Partial<Record<string, ComposerStepStatus>>
  progressPercent: number
} {
  const hasType = draft.docType != null
  const hasClient = Boolean(draft.client?.displayName?.trim())
  const hasLines = draft.products.some((p) => p.label.trim())
  const requiredOk = hasType && hasClient && hasLines
  const controlsOk = requiredOk && blockingErrors === 0

  const stepStatuses: Partial<Record<string, ComposerStepStatus>> = {
    type: hasType ? 'completed' : 'current',
    client: !hasType ? 'upcoming' : hasClient ? 'completed' : 'current',
    lines: !hasClient ? 'upcoming' : hasLines ? 'completed' : 'current',
    required: !hasLines ? 'upcoming' : requiredOk ? 'completed' : 'current',
    controls: !requiredOk ? 'upcoming' : controlsOk ? 'completed' : 'current',
  }

  const done = [hasType, hasClient, hasLines, requiredOk, controlsOk].filter(Boolean).length
  const currentStepId =
    (!hasType && 'type') ||
    (!hasClient && 'client') ||
    (!hasLines && 'lines') ||
    (!requiredOk && 'required') ||
    'controls'

  return {
    currentStepId,
    stepStatuses,
    progressPercent: Math.round((done / COMPOSER_PROGRESS_STEPS.length) * 100),
  }
}

function ClientSection({
  draft,
  onSelect,
  studio = false,
}: {
  draft: FacturationWizardDraft
  onSelect: (client: WizardSelectedClient) => void
  /** Document Studio — pas de titre ComposerSection redondant avec le hero */
  studio?: boolean
}) {
  const c = draft.client
  const body = (
    <>
      <CustomerPicker
        allowCreate
        onSelect={(sel) => {
          onSelect({
            customerId: sel.customerId,
            relationId: sel.relationId,
            displayName: sel.displayName,
            email: sel.email,
            phone: sel.phone,
            address: sel.address,
            source: sel.source,
          })
        }}
        selectedSlot={
          c ? (
            studio ? (
              <StudioClientSmartCard client={c} />
            ) : (
              <div className="fp-composer-client-card" role="status">
                <strong>{c.displayName}</strong>
                <ul className="fp-composer-client-meta">
                  {c.email ? <li>E-mail : {c.email}</li> : <li className="muted">E-mail non renseigné</li>}
                  {c.phone ? <li>Tél. : {c.phone}</li> : null}
                  {c.address ? <li>Adresse : {c.address}</li> : null}
                </ul>
              </div>
            )
          ) : null
        }
      />
      {!c ? (
        <p className="fp-section-inline-hint" role="status">
          Sélectionnez un client pour continuer.
        </p>
      ) : null}
    </>
  )
  if (studio) {
    return (
      <div className="ds-studio-panel" data-ds-panel="client" data-composer-section="client">
        {body}
      </div>
    )
  }
  return (
    <ComposerSection id="client" title="Client" description="Recherchez un client ou ajoutez-en un.">
      {body}
    </ComposerSection>
  )
}

function LineEditor({
  products,
  onChange,
}: {
  products: WizardSelectedProduct[]
  vatRate: number
  onChange: (products: WizardSelectedProduct[]) => void
}) {
  /** Toujours la dernière liste — évite stale closure au clic Supprimer. */
  const productsRef = useRef(products)
  productsRef.current = products
  const [exitingKey, setExitingKey] = useState<string | null>(null)

  const commit = (next: WizardSelectedProduct[]) => {
    onChange(next.map(withLineKey))
  }

  const updateLine = (lineKey: string, patch: Partial<WizardSelectedProduct>) => {
    commit(
      productsRef.current.map((p) =>
        p.lineKey === lineKey ? { ...p, ...patch, lineKey: p.lineKey } : p,
      ),
    )
  }

  /** Suppression atomique immuable par lineKey — source unique draft.products. */
  const removeLine = (lineKey: string) => {
    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const finish = () => {
      commit(productsRef.current.filter((p) => p.lineKey !== lineKey))
      setExitingKey(null)
    }
    if (reducedMotion) {
      finish()
      return
    }
    setExitingKey(lineKey)
    window.setTimeout(finish, 150)
  }

  const duplicateLine = (lineKey: string) => {
    const list = productsRef.current
    const index = list.findIndex((p) => p.lineKey === lineKey)
    if (index < 0) return
    const copy = withLineKey({ ...list[index], lineKey: createLineKey() })
    const next = [...list]
    next.splice(index + 1, 0, copy)
    commit(next)
  }

  const moveLine = (lineKey: string, dir: -1 | 1) => {
    const list = productsRef.current
    const index = list.findIndex((p) => p.lineKey === lineKey)
    if (index < 0) return
    const target = index + dir
    if (target < 0 || target >= list.length) return
    const next = [...list]
    const tmp = next[index]
    next[index] = next[target]
    next[target] = tmp
    commit(next)
  }

  if (!products.length) {
    return (
      <div className="fp-wizard-empty" role="status" data-fp-lines-empty="true">
        Aucune ligne
      </div>
    )
  }

  return (
    <div className="fp-line-editor" aria-label="Éditeur de lignes" data-fp-line-editor="true">
      {products.map((line, index) => {
        const key = line.lineKey ?? `legacy-${index}`
        const exiting = exitingKey === key
        return (
          <div
            key={key}
            className={
              exiting
                ? 'fp-line-editor__row fp-line-editor__row--exiting'
                : 'fp-line-editor__row'
            }
            data-line-key={key}
          >
            <label className="fp-line-editor__field fp-line-editor__field--grow">
              <span>Désignation</span>
              <input
                type="text"
                value={line.label}
                onChange={(e) => updateLine(key, { label: e.target.value })}
                aria-label={`Libellé ligne ${index + 1}`}
              />
            </label>
            <label className="fp-line-editor__field">
              <span>Qté</span>
              <input
                type="number"
                min={0}
                step={1}
                value={line.quantity}
                onChange={(e) => updateLine(key, { quantity: Number(e.target.value) || 0 })}
              />
            </label>
            <label className="fp-line-editor__field">
              <span>Prix HT</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={line.unitPrice}
                onChange={(e) => updateLine(key, { unitPrice: Number(e.target.value) || 0 })}
              />
            </label>
            <label className="fp-line-editor__field">
              <span>TVA %</span>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={line.vatRate}
                onChange={(e) => updateLine(key, { vatRate: Number(e.target.value) || 0 })}
              />
            </label>
            <label className="fp-line-editor__field">
              <span>Remise %</span>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={line.discountPercent ?? 0}
                onChange={(e) =>
                  updateLine(key, { discountPercent: Number(e.target.value) || 0 })
                }
              />
            </label>
            <div className="fp-line-editor__total" aria-label={`Total ligne ${index + 1}`}>
              {formatEuro(lineTotal(line))}
            </div>
            <div className="fp-line-editor__ops" role="group" aria-label={`Actions ligne ${index + 1}`}>
              <button type="button" className="btn secondary" onClick={() => duplicateLine(key)}>
                Dupliquer
              </button>
              <button
                type="button"
                className="btn secondary"
                onClick={() => moveLine(key, -1)}
                disabled={index === 0}
              >
                Monter
              </button>
              <button
                type="button"
                className="btn secondary"
                onClick={() => moveLine(key, 1)}
                disabled={index === products.length - 1}
              >
                Descendre
              </button>
              <button
                type="button"
                className="btn secondary"
                onClick={() => removeLine(key)}
                aria-label={`Supprimer ligne ${index + 1}`}
                disabled={exiting}
              >
                Supprimer
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function LinesSection({
  draft,
  onChange,
  onAppend,
  studio = false,
}: {
  draft: FacturationWizardDraft
  /** Remplace toute la liste (éditeur / remove) — référence déjà normalisée côté parent. */
  onChange: (products: WizardSelectedProduct[], vatRate?: number) => void
  /** Ajout append fonctionnel (évite stale draft.products). */
  onAppend: (product: WizardSelectedProduct, vatRate?: number) => void
  studio?: boolean
}) {
  const { token, orgId } = useAuth()
  const [createOpen, setCreateOpen] = useState(false)
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newPrice, setNewPrice] = useState('0')
  const [createError, setCreateError] = useState('')
  const [pickerKey, setPickerKey] = useState(0)
  const catalogBtnRef = useRef<HTMLButtonElement>(null)

  // Garantit lineKey sur les lignes legacy (une fois).
  useEffect(() => {
    if (!draft.products.some((p) => !p.lineKey)) return
    onChange(draft.products.map(withLineKey))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- normalisation unique
  }, [])

  const addFromSearchResult = (item: SearchResult) => {
    const fields = catalogResultToLineFields(item)
    const next: WizardSelectedProduct = {
      catalogItemId: fields.catalogItemId,
      label: fields.label,
      quantity: 1,
      unitPrice: fields.unitPrice,
      vatRate: fields.vatRate,
      discountPercent: 0,
      lineKey: createLineKey(),
      ...(fields.catalogCreatedAt ? { catalogCreatedAt: fields.catalogCreatedAt } : {}),
    }
    onAppend(next, fields.vatRate)
    setPickerKey((k) => k + 1)
  }

  const addFreeLine = () => {
    onAppend(blankLine(draft.vatRate))
  }

  const createProduct = async () => {
    if (!token || !newName.trim()) return
    setCreateError('')
    try {
      const created = await api.createCatalogItem(
        {
          name: newName.trim(),
          unit_price_ht: Number(newPrice) || 0,
          vat_rate: draft.vatRate,
          active: true,
        },
        token,
        orgId,
      )
      const next: WizardSelectedProduct = {
        catalogItemId: created.id,
        label: created.name,
        quantity: 1,
        unitPrice: created.unit_price_ht,
        vatRate: created.vat_rate,
        discountPercent: 0,
        lineKey: createLineKey(),
      }
      onAppend(next, created.vat_rate)
      setCreateOpen(false)
      setNewName('')
      setNewPrice('0')
      setPickerKey((k) => k + 1)
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Création impossible')
    }
  }

  const body = (
    <>
      <div className="fp-line-actions fp-line-actions--primary" role="group" aria-label="Actions catalogue">
        <div className="fp-line-actions__search">
          <ProductPicker
            key={pickerKey}
            preferredSource={draft.catalogSource === 'inventory' ? 'inventory_pilot' : 'local_catalog'}
            onSelect={addFromSearchResult}
          />
        </div>
        <button
          ref={catalogBtnRef}
          type="button"
          className="btn"
          onClick={() => setCatalogOpen(true)}
          aria-haspopup="dialog"
        >
          Parcourir le catalogue
        </button>
      </div>

      <div
        className="fp-line-actions fp-line-actions--secondary"
        role="group"
        aria-label="Actions secondaires lignes"
      >
        <button type="button" className="btn secondary" onClick={addFreeLine}>
          Ajouter une ligne libre
        </button>
        <button
          type="button"
          className="btn secondary"
          onClick={() => setCreateOpen((v) => !v)}
        >
          {createOpen ? 'Fermer' : 'Nouveau produit'}
        </button>
      </div>

      {createOpen ? (
        <div className="fp-wizard-search__row" style={{ margin: '0.85rem 0' }}>
          <input
            type="text"
            placeholder="Nom produit"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            aria-label="Nom du nouveau produit"
          />
          <input
            type="number"
            placeholder="Prix HT"
            value={newPrice}
            onChange={(e) => setNewPrice(e.target.value)}
            step="0.01"
            min="0"
            aria-label="Prix HT du nouveau produit"
          />
          <button
            type="button"
            className="btn"
            disabled={!newName.trim()}
            onClick={() => void createProduct()}
          >
            Ajouter
          </button>
        </div>
      ) : null}
      {createError ? <p className="error">{createError}</p> : null}

      {!draft.products.some((p) => p.label.trim()) ? (
        <p className="fp-section-inline-hint" role="status">
          Ajoutez au moins une ligne avec une désignation.
        </p>
      ) : null}

      {studio ? (
        <StudioProductsSmartCard products={draft.products} lineTotal={lineTotal} />
      ) : null}

      <LineEditor
        products={draft.products}
        vatRate={draft.vatRate}
        onChange={(products) => onChange(products)}
      />

      <LibraryCatalogModal
        open={catalogOpen}
        onOpenChange={setCatalogOpen}
        onAddResource={addFromSearchResult}
        returnFocusRef={catalogBtnRef}
        defaultVatRate={draft.vatRate}
      />
    </>
  )

  if (studio) {
    return (
      <div className="ds-studio-panel" data-ds-panel="items" data-composer-section="lines">
        {body}
      </div>
    )
  }

  return (
    <ComposerSection
      id="lines"
      title="Produits"
      description="Recherchez un produit ou parcourez le catalogue. Les lignes libres et la création restent en actions secondaires."
    >
      {body}
    </ComposerSection>
  )
}

export type FacturationComposerCloseOptions = {
  docId?: number | null
  reopenCreate?: boolean
}

export type FacturationComposerPageProps = {
  /** `modal` = dans ComposerDialog ; `page` = legacy / tests plein viewport */
  presentation?: 'page' | 'modal'
  onRequestClose?: (opts?: FacturationComposerCloseOptions) => void
  /** Bloque dismiss Escape/backdrop du dialog parent quand dirty confirm ouvert */
  onDismissBlockChange?: (blocked: boolean) => void
  /** Type persisté par la state machine (évite redirect si URL pas encore sync) */
  forcedDocType?: CommercialDocType | null
  /** Sync stage confirmation → DocumentCreateFlow */
  onCreationConfirmChange?: (open: boolean) => void
}

export default function FacturationComposerPage({
  presentation = 'page',
  onRequestClose,
  onDismissBlockChange,
  forcedDocType = null,
  onCreationConfirmChange,
}: FacturationComposerPageProps) {
  const { token, orgId, memberships = [] } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const typeFromUrl = parseDocType(searchParams.get('type'))
  /** Source de vérité type : prop machine > URL — Composer vide reste valide */
  const typeParam = forcedDocType ?? typeFromUrl
  const prefillCustomerIdRaw = searchParams.get('customer_id')
  const prefillCustomerId = prefillCustomerIdRaw ? Number(prefillCustomerIdRaw) : null
  const isModal = presentation === 'modal'

  const activeMembership = useMemo(
    () => (memberships ?? []).find((m) => m.organization_id === orgId) ?? null,
    [memberships, orgId],
  )
  const canEditDoc = useMemo(() => {
    const perms = activeMembership?.permissions || []
    return (
      perms.includes('*') ||
      perms.includes('invoice.create') ||
      perms.includes('quote.create')
    )
  }, [activeMembership])
  const canManageLogo = useMemo(() => {
    const perms = activeMembership?.permissions || []
    return perms.includes('*') || perms.includes('settings.manage')
  }, [activeMembership])

  const [draft, setDraft] = useState<FacturationWizardDraft>(() =>
    createEmptyFacturationDraft({
      catalogSource: isInventoryCatalogAvailable() ? 'inventory' : 'local',
      docType: typeParam,
    }),
  )
  const [orgBrand, setOrgBrand] = useState<OrgDetail['organization'] | null>(null)
  const brandingInitRef = useRef(false)
  const [busy, setBusy] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  const [actionError, setActionError] = useState('')
  const [prefillDone, setPrefillDone] = useState(false)
  const [previewCollapsed, setPreviewCollapsed] = useState(false)
  const [autosave, setAutosave] = useState<ComposerAutosaveState>({ status: 'idle' })
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfState, setPdfState] = useState<ComposerPreviewState>('empty')
  const [pdfError, setPdfError] = useState('')
  const [docSent, setDocSent] = useState(false)
  const [pdfZoom, setPdfZoom] = useState(100)
  const [pdfFitWidth, setPdfFitWidth] = useState(true)
  const [pdfFullscreen, setPdfFullscreen] = useState(false)
  const [pdfPage, setPdfPage] = useState(1)
  const [previewMode, setPreviewMode] = useState<'live' | 'pdf'>('live')
  const [exitConfirmOpen, setExitConfirmOpen] = useState(false)
  const [exitSaveError, setExitSaveError] = useState('')
  const [creationConfirmOpen, setCreationConfirmOpen] = useState(false)
  /** Parcours guidé modal (F1.3.2) — distinct de ComposerModalStage */
  const [guidedStep, setGuidedStep] = useState<ComposerStep>('client')
  const [stepGateMessage, setStepGateMessage] = useState('')
  const stepHeadingRef = useRef<HTMLHeadingElement>(null)
  const autosaveTimer = useRef<number | null>(null)
  const pdfReloadTimer = useRef<number | null>(null)
  const pdfUrlRef = useRef<string | null>(null)
  const pdfGenerationRef = useRef(0)
  const loadPdfRef = useRef<((docId?: number | null) => Promise<void>) | null>(null)
  const dirtyRef = useRef(false)
  /** Epoch draft — ignore effets côté autosave si état local a avancé. */
  const draftEpochRef = useRef(0)
  const draftRef = useRef(draft)
  draftRef.current = draft

  const bumpDraftEpoch = () => {
    draftEpochRef.current += 1
  }

  const focus = useComposerFocus({
    initialEnabled: true,
    exitTargets: [
      {
        id: 'documents',
        label: 'Documents',
        href: '/facturation/documents',
        description: 'Retour à la liste des documents',
      },
    ],
    onExitNavigate: (href) => {
      if (isModal && onRequestClose) {
        onRequestClose()
        return
      }
      navigate(href)
    },
  })

  useEffect(() => {
    if (typeParam && draft.docType !== typeParam) {
      setDraft((d) => ({ ...d, docType: typeParam }))
    }
  }, [typeParam, draft.docType])

  /** Charge identité org pour preview + default showLogo (une fois). */
  useEffect(() => {
    if (!token || orgId == null) return
    let cancelled = false
    api
      .orgDetail(orgId, token)
      .then((res) => {
        if (cancelled) return
        const organization = res.organization
        setOrgBrand(organization)
        if (!brandingInitRef.current) {
          brandingInitRef.current = true
          const showLogo = resolveShowLogoDefault({
            draftShowLogo: null,
            orgPreference: organization.documents_show_logo,
            hasPdfSafeLogo: hasAnyLogoUrl(organization.logo),
          })
          setDraft((d) => ({ ...d, documentBranding: { showLogo } }))
        }
      })
      .catch(() => {
        /* preview sans org — nom générique */
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  const applyBrandingChange = useCallback(
    (
      next: FacturationWizardDraft['documentBranding'],
      opts?: { persistOrgDefault?: boolean },
    ) => {
      dirtyRef.current = true
      setDraft((d) => ({ ...d, documentBranding: next }))
      if (opts?.persistOrgDefault && canManageLogo && token && orgId != null) {
        void api
          .updateOrganization(
            orgId,
            { documents_show_logo: next.showLogo },
            token,
          )
          .then((res) => setOrgBrand(res.organization))
          .catch(() => {
            /* préférence org optionnelle — ne bloque pas le draft */
          })
      }
    },
    [canManageLogo, token, orgId],
  )

  useEffect(() => {
    if (isModal) {
      delete document.body.dataset.fpFullFocus
      document.body.dataset.fpFocus = 'modal'
      return () => {
        delete document.body.dataset.fpFocus
      }
    }
    document.body.dataset.fpFocus = focus.focusMode ? 'true' : 'false'
    document.body.dataset.fpFullFocus = focus.focusMode ? 'true' : 'false'
    return () => {
      delete document.body.dataset.fpFocus
      delete document.body.dataset.fpFullFocus
    }
  }, [focus.focusMode, isModal])

  useEffect(() => {
    onDismissBlockChange?.(exitConfirmOpen)
  }, [exitConfirmOpen, onDismissBlockChange])

  useEffect(() => {
    onCreationConfirmChange?.(creationConfirmOpen)
  }, [creationConfirmOpen, onCreationConfirmChange])

  useEffect(() => {
    if (!token || orgId == null || !prefillCustomerId || Number.isNaN(prefillCustomerId)) return
    if (prefillDone) return
    let cancelled = false
    void api
      .getCustomer(prefillCustomerId, token, orgId)
      .then((c) => {
        if (cancelled) return
        setDraft((d) => ({
          ...d,
          client: {
            customerId: c.id,
            relationId: null,
            displayName: c.name,
            email: c.email || '',
            phone: c.phone,
            address: c.address,
            source: 'billing_customer',
          },
        }))
        setPrefillDone(true)
      })
      .catch(() => setPrefillDone(true))
    return () => {
      cancelled = true
    }
  }, [token, orgId, prefillCustomerId, prefillDone])

  const controls = useMemo(() => mapControls(deriveWizardControls(draft)), [draft])
  const blockingErrors = controls.filter((c) => c.severity === 'error').length
  const liveTotals = useMemo(() => snapshotLiveTotals(draft), [draft])
  const ht = liveTotals.ht
  const tva = liveTotals.tva
  const ttc = liveTotals.ttc
  const liveInsights = useMemo(
    () => deriveLiveDocumentInsights({ draft, issues: controls }),
    [draft, controls],
  )
  const liveStatus = useMemo(
    () =>
      deriveLiveDocumentStatus({
        createdDocId: draft.createdDocId,
        sent: docSent,
        issues: controls,
        autosave,
        hasDocType: draft.docType != null,
        hasClient: Boolean(draft.client?.displayName?.trim()),
        hasProducts: draft.products.some((p) => p.label.trim()),
      }),
    [draft, docSent, controls, autosave],
  )
  const progress = useMemo(() => deriveProgress(draft, blockingErrors), [draft, blockingErrors])

  const guidedStatuses = useMemo(
    () => deriveGuidedStepStatuses(guidedStep),
    [guidedStep],
  )

  useEffect(() => {
    if (!isModal) return
    setStepGateMessage('')
    const t = window.setTimeout(() => {
      stepHeadingRef.current?.focus()
    }, 0)
    return () => window.clearTimeout(t)
  }, [guidedStep, isModal])

  const goNextStep = useCallback(() => {
    const gate = validateComposerStep(guidedStep, draft, blockingErrors)
    if (!gate.ok) {
      setStepGateMessage(gate.message ?? 'Complétez cette étape pour continuer.')
      return
    }
    setStepGateMessage('')
    const next = nextComposerStep(guidedStep)
    if (next) setGuidedStep(next)
  }, [guidedStep, draft, blockingErrors])

  const goPrevStep = useCallback(() => {
    setStepGateMessage('')
    const prev = prevComposerStep(guidedStep)
    if (prev) setGuidedStep(prev)
  }, [guidedStep])

  const jumpToStep = useCallback(
    (stepId: string) => {
      if (!isComposerStep(stepId)) return
      const statuses = deriveGuidedStepStatuses(guidedStep)
      if (statuses[stepId] !== 'completed' && stepId !== guidedStep) return
      setStepGateMessage('')
      setGuidedStep(stepId)
    },
    [guidedStep],
  )

  const patchDraft = useCallback((patch: Partial<FacturationWizardDraft>) => {
    dirtyRef.current = true
    if (patch.products) bumpDraftEpoch()
    setDraft((d) => ({ ...d, ...patch }))
  }, [])

  /** Remplace products de façon atomique (éditeur / remove) — nouvelle référence. */
  const replaceProducts = useCallback((products: WizardSelectedProduct[], vatRate?: number) => {
    dirtyRef.current = true
    bumpDraftEpoch()
    setDraft((d) => ({
      ...d,
      products: products.map(withLineKey),
      ...(vatRate != null ? { vatRate } : {}),
    }))
  }, [])

  /** Append fonctionnel — jamais `[...draft.products]` stale. */
  const appendProduct = useCallback((product: WizardSelectedProduct, vatRate?: number) => {
    dirtyRef.current = true
    bumpDraftEpoch()
    setDraft((d) => ({
      ...d,
      products: [...d.products, withLineKey(product)],
      ...(vatRate != null ? { vatRate } : {}),
    }))
  }, [])

  const buildPayload = useCallback(() => {
    const current = draftRef.current
    if (!current.docType || !current.client) return null
    const lines = current.products
      .filter((p) => p.label.trim())
      .map((p) => ({
        label: p.label.trim(),
        quantity: p.quantity,
        unit_price: p.unitPrice,
        catalog_item_id: p.catalogItemId,
      }))
    const totals = snapshotLiveTotals(current)
    return {
      doc_type: current.docType,
      customer_name: current.client.displayName,
      customer_email: current.client.email || undefined,
      customer_id: current.client.customerId,
      amount_ht: totals.ht,
      vat_rate: current.vatRate,
      notes: current.notes || undefined,
      due_days: current.dueDays,
      lines,
      branding: {
        showLogo: current.documentBranding.showLogo,
        template: 'premium_v1',
      },
    }
  }, [])

  const saveDraft = useCallback(
    async (opts?: { silent?: boolean; skipConfirm?: boolean }): Promise<number | null> => {
      if (!token) return null
      const epochAtStart = draftEpochRef.current
      const payload = buildPayload()
      if (!payload) {
        if (!opts?.silent) {
          setActionError('Complétez le client et au moins une ligne avant d’enregistrer.')
        }
        return null
      }
      const existingId = draftRef.current.createdDocId
      setBusy(true)
      setAutosave({ status: 'saving' })
      if (!opts?.silent) {
        setActionError('')
        setActionMessage('')
      }
      try {
        let doc
        if (existingId) {
          doc = await api.updateSalesDoc(
            existingId,
            {
              customer_name: payload.customer_name,
              customer_email: payload.customer_email,
              customer_id: payload.customer_id,
              amount_ht: payload.amount_ht,
              vat_rate: payload.vat_rate,
              notes: payload.notes,
              due_days: payload.due_days,
              lines: payload.lines,
              branding: payload.branding,
            },
            token,
            orgId,
          )
        } else {
          doc = await api.createSalesDoc(payload, token, orgId)
        }
        /* Jamais réinjecter products depuis la réponse — ids seulement. */
        setDraft((d) => ({
          ...d,
          createdDocId: doc.id,
          createdDocNumber: doc.number,
        }))
        const localAdvanced = epochAtStart !== draftEpochRef.current
        if (!localAdvanced) {
          dirtyRef.current = false
        }
        setAutosave({ status: 'saved', savedAt: Date.now() })
        if (!opts?.silent) setActionMessage(`Brouillon enregistré : ${doc.number}`)
        if (!existingId && !opts?.skipConfirm && !localAdvanced) {
          setCreationConfirmOpen(true)
        }
        if (existingId || doc.id) {
          if (pdfReloadTimer.current != null) window.clearTimeout(pdfReloadTimer.current)
          pdfReloadTimer.current = window.setTimeout(() => {
            void loadPdfRef.current?.(doc.id)
          }, 700)
        }
        /* Si l’utilisateur a modifié pendant le save → re-planifier (last-write-wins). */
        if (localAdvanced && doc.id) {
          if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current)
          autosaveTimer.current = window.setTimeout(() => {
            void saveDraft({ silent: true, skipConfirm: true })
          }, 400)
        }
        return doc.id
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Enregistrement impossible'
        setAutosave({
          status: 'error',
          message,
          onRetry: () => void saveDraft(opts),
        })
        if (!opts?.silent) setActionError(message)
        return null
      } finally {
        setBusy(false)
      }
    },
    [token, orgId, buildPayload],
  )

  useEffect(() => {
    if (!draft.createdDocId || !draft.docType || !draft.client) return
    if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current)
    autosaveTimer.current = window.setTimeout(() => {
      void saveDraft({ silent: true })
    }, 2500)
    return () => {
      if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce on meaningful draft fields
  }, [
    draft.createdDocId,
    draft.docType,
    draft.client,
    draft.products,
    draft.vatRate,
    draft.notes,
    draft.dueDays,
    draft.documentBranding,
  ])

  const loadPdf = useCallback(
    async (docId?: number | null) => {
      const id = docId ?? draft.createdDocId
      if (!token || !id) {
        setPdfState('empty')
        setPdfUrl(null)
        return
      }
      const generation = ++pdfGenerationRef.current
      setPdfState('loading')
      setPdfError('')
      try {
        const url = await api.openSalesDocPdfBlob(id, token, orgId)
        if (generation !== pdfGenerationRef.current) {
          URL.revokeObjectURL(url)
          return
        }
        if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current)
        pdfUrlRef.current = url
        setPdfUrl(url)
        setPdfState('ready')
        setPreviewMode((m) => (m === 'live' && pdfUrlRef.current ? m : 'pdf'))
      } catch (e) {
        if (generation !== pdfGenerationRef.current) return
        setPdfState('error')
        setPdfError(e instanceof Error ? e.message : 'PDF indisponible')
      }
    },
    [token, orgId, draft.createdDocId],
  )

  loadPdfRef.current = loadPdf

  useEffect(() => {
    if (!draft.createdDocId) {
      setPdfState('empty')
      setPdfUrl(null)
      setPreviewMode('live')
      return
    }
    void loadPdf(draft.createdDocId)
    return () => {
      if (pdfUrlRef.current) {
        URL.revokeObjectURL(pdfUrlRef.current)
        pdfUrlRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.createdDocId])

  useEffect(() => {
    return () => {
      if (pdfReloadTimer.current != null) window.clearTimeout(pdfReloadTimer.current)
    }
  }, [])

  const sendDoc = async () => {
    if (!token || !draft.createdDocId) {
      setActionError('Enregistrez d’abord un brouillon pour pouvoir envoyer.')
      return
    }
    setBusy(true)
    setActionError('')
    try {
      await api.billingAction(draft.createdDocId, 'sign', token, orgId)
      setDocSent(true)
      setCreationConfirmOpen(true)
      setActionMessage('Document marqué comme envoyé.')
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Envoi impossible')
    } finally {
      setBusy(false)
    }
  }

  const downloadPdf = async () => {
    if (!token || !draft.createdDocId) {
      setActionError('Enregistrez d’abord un brouillon pour télécharger le PDF.')
      return
    }
    setBusy(true)
    setActionError('')
    try {
      await api.downloadSalesDocPdf(
        draft.createdDocId,
        token,
        orgId,
        draft.createdDocNumber || undefined,
      )
      setActionMessage('Téléchargement PDF lancé.')
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'PDF indisponible')
    } finally {
      setBusy(false)
    }
  }

  const exitToDocuments = useCallback(
    (opts?: FacturationComposerCloseOptions) => {
      if (isModal && onRequestClose) {
        onRequestClose(
          opts ?? (draft.createdDocId ? { docId: draft.createdDocId } : undefined),
        )
        return
      }
      if (opts?.reopenCreate) {
        navigate('/facturation/documents?create=1')
        return
      }
      if (opts?.docId != null || draft.createdDocId) {
        navigate(`/facturation/documents?doc=${opts?.docId ?? draft.createdDocId}`)
        return
      }
      navigate('/facturation/documents')
    },
    [draft.createdDocId, navigate, isModal, onRequestClose],
  )

  const hasUnsavedLocalWork = useCallback(() => {
    return (
      dirtyRef.current ||
      Boolean(draft.client) ||
      draft.products.some((p) => p.label.trim() || p.unitPrice > 0) ||
      Boolean(draft.notes.trim())
    )
  }, [draft])

  const requestExit = useCallback(() => {
    // Autosaved (createdDocId, pas dirty) → fermeture directe
    if (draft.createdDocId && !dirtyRef.current) {
      exitToDocuments({ docId: draft.createdDocId })
      return
    }
    // Sans modification locale → fermeture
    if (!draft.createdDocId && !hasUnsavedLocalWork()) {
      exitToDocuments()
      return
    }
    // Unsaved / dirty → confirm 3 actions
    if (hasUnsavedLocalWork() || dirtyRef.current) {
      setExitSaveError('')
      setExitConfirmOpen(true)
      return
    }
    exitToDocuments(draft.createdDocId ? { docId: draft.createdDocId } : undefined)
  }, [draft.createdDocId, exitToDocuments, hasUnsavedLocalWork])

  const saveAndClose = useCallback(async () => {
    setExitSaveError('')
    const docId = await saveDraft({ skipConfirm: true })
    if (docId != null) {
      setExitConfirmOpen(false)
      exitToDocuments({ docId })
      return
    }
    setExitSaveError(
      'Impossible d’enregistrer le brouillon. Vérifiez le client et les lignes, puis réessayez.',
    )
  }, [saveDraft, exitToDocuments])

  const docTypeLabel = draft.docType
    ? DOC_TYPE_CARDS.find((c) => c.type === draft.docType)?.name
    : undefined

  const definition: ComposerDefinition = useMemo(
    () => ({
      id: 'facturation-document-composer',
      title: draft.createdDocNumber
        ? `Document ${draft.createdDocNumber}`
        : composerTitle(draft.docType),
      documentType: docTypeLabel,
      status: liveStatus.status,
      statusLabel: liveStatus.label,
      statusHint: liveStatus.explanation,
      statusIcon: liveStatus.icon,
      steps: isModal ? GUIDED_PROGRESS_STEPS : COMPOSER_PROGRESS_STEPS,
      currentStepId: isModal ? guidedStep : progress.currentStepId,
      stepStatuses: isModal ? guidedStatuses : progress.stepStatuses,
      progressPercent: isModal
        ? guidedProgressPercent(guidedStep)
        : progress.progressPercent,
      autosave,
    }),
    [
      draft.createdDocNumber,
      draft.docType,
      docTypeLabel,
      liveStatus,
      progress,
      autosave,
      isModal,
      guidedStep,
      guidedStatuses,
    ],
  )

  const headerIssues = controls.filter((c) => c.severity === 'error' || c.severity === 'warning')

  const primaryActions: ComposerActionDef[] = useMemo(() => {
    const actions: ComposerActionDef[] = []
    if (draft.createdDocId && blockingErrors === 0) {
      actions.push({
        id: 'send',
        label: docSent ? 'Renvoyer' : 'Continuer envoi',
        tone: 'primary',
        disabled: busy,
        onClick: () => void sendDoc(),
      })
    } else if (draft.createdDocId) {
      actions.push({
        id: 'draft',
        label: busy && autosave.status === 'saving' ? 'Enregistrement…' : 'Enregistrer brouillon',
        tone: 'primary',
        disabled: busy,
        loading: busy && autosave.status === 'saving',
        onClick: () => void saveDraft(),
      })
    } else {
      actions.push({
        id: 'save',
        label: busy ? 'Enregistrement…' : 'Enregistrer brouillon',
        tone: 'primary',
        disabled: busy,
        onClick: () => void saveDraft(),
      })
    }
    return actions.slice(0, 1)
  }, [busy, autosave.status, draft.createdDocId, blockingErrors, docSent, saveDraft])

  const secondaryActions: ComposerActionDef[] = useMemo(() => {
    const actions: ComposerActionDef[] = [
      {
        id: 'cancel',
        label: 'Annuler',
        tone: 'ghost',
        onClick: requestExit,
      },
    ]
    if (draft.createdDocId && blockingErrors === 0) {
      actions.push({
        id: 'draft',
        label: busy && autosave.status === 'saving' ? 'Enregistrement…' : 'Enregistrer brouillon',
        tone: 'secondary',
        disabled: busy,
        loading: busy && autosave.status === 'saving',
        onClick: () => void saveDraft(),
      })
    } else if (headerIssues.length > 0) {
      actions.push({
        id: 'verify',
        label: 'Vérifier',
        tone: 'secondary',
        onClick: () => {
          document
            .querySelector('[data-composer-section="controls"]')
            ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        },
      })
    }
    return actions.slice(0, 2)
  }, [
    requestExit,
    draft.createdDocId,
    blockingErrors,
    busy,
    autosave.status,
    saveDraft,
    headerIssues.length,
  ])

  const structuredPreview = useMemo(
    () => (
      <StudioLivingPdf
        docType={draft.docType}
        docTypeLabel={docTypeLabel}
        client={draft.client}
        products={draft.products}
        notes={draft.notes}
        dueDays={liveTotals.dueDays}
        dueDateLabel={liveTotals.dueDateLabel}
        vatRate={draft.vatRate}
        ht={ht}
        tva={tva}
        ttc={ttc}
        discountTotal={liveTotals.discountTotal}
        docNumber={draft.createdDocNumber}
        lineTotal={lineTotal}
        org={(orgBrand as OrgDocumentBrandInput | null) ?? undefined}
        branding={draft.documentBranding}
      />
    ),
    [docTypeLabel, draft, liveTotals, ht, tva, ttc, orgBrand],
  )

  const pdfSrc =
    pdfUrl && pdfPage > 1 ? `${pdfUrl}#page=${pdfPage}` : pdfUrl ?? undefined

  const previewToolbar = (
    <div className="ld-preview-toolbar" role="group" aria-label="Mode aperçu">
      <button
        type="button"
        className="elf-cmp-action elf-cmp-action--ghost"
        aria-pressed={previewMode === 'live'}
        onClick={() => setPreviewMode('live')}
      >
        Live
      </button>
      <button
        type="button"
        className="elf-cmp-action elf-cmp-action--ghost"
        aria-pressed={previewMode === 'pdf'}
        disabled={!pdfUrl}
        onClick={() => setPreviewMode('pdf')}
      >
        PDF
      </button>
    </div>
  )

  const previewSlot = (
    <ComposerPreview
      state={
        previewMode === 'pdf'
          ? pdfState === 'ready' && pdfUrl
            ? 'ready'
            : pdfState
          : 'ready'
      }
      title={previewMode === 'pdf' ? 'Aperçu PDF' : 'Aperçu'}
      errorMessage={pdfError}
      onRetry={() => void loadPdf()}
      onDownload={draft.createdDocId ? () => void downloadPdf() : undefined}
      zoomPercent={pdfZoom}
      onZoomIn={() => setPdfZoom((z) => Math.min(200, z + 10))}
      onZoomOut={() => setPdfZoom((z) => Math.max(50, z - 10))}
      onZoomReset={() => {
        setPdfZoom(100)
        setPdfFitWidth(false)
      }}
      onFitWidth={() => setPdfFitWidth((v) => !v)}
      fitWidth={pdfFitWidth}
      onToggleFullscreen={() => setPdfFullscreen((v) => !v)}
      fullscreen={pdfFullscreen}
      page={pdfPage}
      onPageChange={setPdfPage}
      toolbar={previewToolbar}
    >
      <div
        className={`ld-preview-viewport${pdfFitWidth ? ' is-fit-width' : ''}`}
        data-preview-mode={previewMode}
      >
        <div
          className="ld-preview-scaled"
          style={{ transform: `scale(${pdfZoom / 100})` }}
        >
          {previewMode === 'pdf' && pdfSrc ? (
            <iframe title={`PDF ${draft.createdDocNumber || 'document'}`} src={pdfSrc} />
          ) : (
            structuredPreview
          )}
        </div>
      </div>
    </ComposerPreview>
  )

  /*
   * F1.3.1.3 — Ne jamais redirect auto si Composer « vide » (pas client / pas lignes).
   * Mode modal : type vient de la machine (forcedDocType) ; loading/erreur restent dans le modal.
   * Mode page (legacy/tests) : sans type → message dans la page, pas de bounce silencieux.
   */
  if (!typeParam) {
    if (isModal) {
      return (
        <div className="fp-composer-dialog__bridging" role="status" aria-live="polite">
          Préparation du document…
        </div>
      )
    }
    return (
      <div className="panel form-error" role="alert">
        Type de document manquant.{' '}
        <Link to="/facturation/documents?create=1">Choisir un type</Link>
      </div>
    )
  }

  const freeformBody: ReactNode = (
    <>
      <ClientSection draft={draft} onSelect={(client) => patchDraft({ client })} />
      <LinesSection
        draft={draft}
        onChange={replaceProducts}
        onAppend={appendProduct}
      />
      <ComposerSection id="conditions" title="Conditions" description="Échéance et TVA du document.">
        <div className="fp-composer-fields">
          <label className="fp-composer-inspector-field">
            Échéance (jours)
            <input
              type="number"
              min={0}
              value={draft.dueDays}
              onChange={(e) => patchDraft({ dueDays: Number(e.target.value) || 0 })}
            />
          </label>
          <label className="fp-composer-inspector-field">
            TVA document (%)
            <input
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={draft.vatRate}
              onChange={(e) => patchDraft({ vatRate: Number(e.target.value) || 0 })}
            />
          </label>
        </div>
      </ComposerSection>
      <ComposerSection id="notes" title="Notes" description="Mentions libres sur le document.">
        <label className="fp-composer-inspector-field">
          Notes
          <textarea
            rows={3}
            value={draft.notes}
            onChange={(e) => patchDraft({ notes: e.target.value })}
            aria-label="Notes document"
          />
        </label>
      </ComposerSection>
      <ComposerSection
        id="payment"
        title="Paiement"
        description="Le suivi des paiements reste disponible depuis Documents après enregistrement."
      >
        {draft.createdDocId ? (
          <p className="muted">
            Document {draft.createdDocNumber}.{' '}
            <Link to={`/facturation/documents?doc=${draft.createdDocId}`}>
              Ouvrir dans Documents
            </Link>
          </p>
        ) : (
          <p className="muted">Enregistrez le brouillon pour accéder au paiement.</p>
        )}
      </ComposerSection>
      <ComposerSection id="totals" title="Totaux" description="Calculés à partir des lignes.">
        <LiveTotals totals={liveTotals} vatRate={draft.vatRate} />
      </ComposerSection>
      <ComposerSection id="preview-inline" title="Aperçu" description="Résumé du document en cours.">
        {structuredPreview}
      </ComposerSection>
      <ComposerSection
        id="controls"
        title="Contrôles"
        description="Points à corriger avant envoi."
      >
        <ComposerValidation issues={controls} emptyMessage="Aucun contrôle bloquant." />
        {liveInsights.length > 0 ? (
          <LiveInsightsPanel insights={liveInsights} emptyMessage="" />
        ) : null}
        {actionMessage ? <p className="success">{actionMessage}</p> : null}
        {actionError ? <p className="error">{actionError}</p> : null}
      </ComposerSection>
    </>
  )

  const stepMeta = getComposerStepMeta(guidedStep)
  const studioIcon = STUDIO_STEP_ICONS[guidedStep] ?? 'client'
  const conseilExample = STUDIO_CONSEIL_EXAMPLES[guidedStep]

  const guidedBody: ReactNode = (
    <section
      className="fp-guided-step ds-studio-step"
      data-fp-guided-step={guidedStep}
      data-ds-studio-step={guidedStep}
      aria-labelledby="fp-guided-step-heading"
    >
      <StudioStepHero
        title={stepMeta.title}
        help={stepMeta.description}
        icon={studioIcon}
        headingRef={stepHeadingRef}
      />

      {guidedStep === 'client' ? (
        <>
          <ClientSection
            draft={draft}
            onSelect={(client) => patchDraft({ client })}
            studio
          />
          {conseilExample ? <StudioConseilPlaceholder example={conseilExample} /> : null}
        </>
      ) : null}

      {guidedStep === 'items' ? (
        <>
          <LinesSection
            draft={draft}
            onChange={replaceProducts}
            onAppend={appendProduct}
            studio
          />
          {conseilExample ? <StudioConseilPlaceholder example={conseilExample} /> : null}
        </>
      ) : null}

      {guidedStep === 'terms' ? (
        <div className="ds-studio-panel" data-fp-guided-panel="terms" data-ds-panel="terms">
          <div className="fp-composer-fields">
            <label className="fp-composer-inspector-field">
              Échéance (jours)
              <input
                type="number"
                min={0}
                value={draft.dueDays}
                onChange={(e) => patchDraft({ dueDays: Number(e.target.value) || 0 })}
              />
            </label>
            <label className="fp-composer-inspector-field">
              TVA document (%)
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={draft.vatRate}
                onChange={(e) => patchDraft({ vatRate: Number(e.target.value) || 0 })}
              />
            </label>
          </div>
        </div>
      ) : null}

      {guidedStep === 'notes_payment' ? (
        <div className="ds-studio-panel" data-ds-panel="notes_payment">
          <ComposerSection id="notes" title="Notes" description="Mentions libres sur le document.">
            <label className="fp-composer-inspector-field">
              Notes
              <textarea
                rows={3}
                value={draft.notes}
                onChange={(e) => patchDraft({ notes: e.target.value })}
                aria-label="Notes document"
              />
            </label>
          </ComposerSection>
          <ComposerSection
            id="payment"
            title="Paiement"
            description="Le suivi des paiements reste disponible depuis Documents après enregistrement."
          >
            {draft.createdDocId ? (
              <p className="muted">
                Document {draft.createdDocNumber}.{' '}
                <Link to={`/facturation/documents?doc=${draft.createdDocId}`}>
                  Ouvrir dans Documents
                </Link>
              </p>
            ) : (
              <p className="muted">Enregistrez le brouillon pour accéder au paiement.</p>
            )}
          </ComposerSection>
        </div>
      ) : null}

      {guidedStep === 'review' ? (
        <>
          <div className="ds-studio-panel" data-ds-panel="review">
            <ComposerSection
              id="identity"
              title="Identité visuelle"
              description="Logo et présentation du document."
            >
              <IdentityVisualSection
                branding={draft.documentBranding}
                org={orgBrand}
                canEditDoc={canEditDoc}
                canManageLogo={canManageLogo}
                token={token}
                orgId={orgId}
                onBrandingChange={applyBrandingChange}
                onOrgUpdated={setOrgBrand}
              />
            </ComposerSection>
            <ComposerSection id="totals" title="Totaux" description="Calculés à partir des lignes.">
              <LiveTotals totals={liveTotals} vatRate={draft.vatRate} />
            </ComposerSection>
            <ComposerSection
              id="controls"
              title="Contrôles"
              description="Points à corriger avant envoi."
            >
              <ComposerValidation issues={controls} emptyMessage="Aucun contrôle bloquant." />
              {liveInsights.length > 0 ? (
                <LiveInsightsPanel insights={liveInsights} emptyMessage="" />
              ) : null}
            </ComposerSection>
            {draft.client || draft.products.some((p) => p.label.trim()) ? (
              <ComposerSection id="review-summary" title="Résumé" description="Aperçu textuel du document.">
                {structuredPreview}
              </ComposerSection>
            ) : null}
          </div>
          {conseilExample ? <StudioConseilPlaceholder example={conseilExample} /> : null}
        </>
      ) : null}

      {guidedStep === 'finalization' ? (
        <div className="ds-studio-panel" data-ds-panel="finalization">
          <ComposerSection
            id="finalization"
            title="Actions"
            description="Enregistrez le brouillon ou préparez l’envoi. Les actions ci-dessous sont réelles."
          >
            <div className="fp-guided-finalization-actions" role="group" aria-label="Finalisation">
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => void saveDraft()}
              >
                {busy ? 'Enregistrement…' : 'Enregistrer le brouillon'}
              </button>
              {draft.createdDocId && blockingErrors === 0 ? (
                <button
                  type="button"
                  className="btn"
                  disabled={busy}
                  onClick={() => void sendDoc()}
                >
                  {docSent ? 'Renvoyer' : 'Envoyer'}
                </button>
              ) : null}
            </div>
            {actionMessage ? <p className="success">{actionMessage}</p> : null}
            {actionError ? <p className="error">{actionError}</p> : null}
            <p className="muted fp-guided-step__hint">
              L’aperçu à droite reste synchronisé. Fermez le modal pour revenir aux Documents.
            </p>
          </ComposerSection>
        </div>
      ) : null}

      {stepGateMessage ? (
        <p className="fp-guided-step__gate" role="alert">
          {stepGateMessage}
        </p>
      ) : null}
    </section>
  )

  const guidedFooter =
    isModal && !creationConfirmOpen ? (
      <div className="fp-guided-footer" role="group" aria-label="Navigation des étapes">
        <button
          type="button"
          className="btn secondary"
          disabled={guidedStep === 'client'}
          onClick={goPrevStep}
        >
          Retour
        </button>
        {guidedStep !== 'finalization' ? (
          <button type="button" className="btn" onClick={goNextStep}>
            Continuer
          </button>
        ) : (
          <span className="muted" aria-hidden="true" />
        )}
      </div>
    ) : null

  return (
    <div
      data-fp-space="nouveau"
      data-fp-composer="f131"
      data-fp-guided={isModal ? '1' : undefined}
      data-fp-focus={isModal ? 'modal' : focus.focusMode ? '1' : '0'}
      data-fp-full-focus={isModal ? undefined : '1'}
      data-fp-composer-presentation={presentation}
      data-ds-studio={isModal ? '1' : undefined}
      className={isModal ? 'fp-composer-modal-root ds-studio' : undefined}
    >
      <ComposerFocusLayout
        definition={definition}
        onBack={requestExit}
        backLabel="Documents"
        previewCollapsed={previewCollapsed}
        onTogglePreview={() => setPreviewCollapsed((v) => !v)}
        primaryActions={isModal && guidedStep === 'finalization' ? primaryActions : isModal ? [] : primaryActions}
        secondaryActions={secondaryActions}
        preview={previewSlot}
        onSelectStep={isModal ? jumpToStep : undefined}
        className={isModal ? 'elf-cmp-focus--modal elf-cmp-focus--guided elf-cmp-focus--studio' : undefined}
        headerCenter={
          headerIssues.length > 0 ? (
            <p className="fp-composer-header-summary" role="status">
              {headerIssues.length} point{headerIssues.length > 1 ? 's' : ''} à vérifier
            </p>
          ) : null
        }
        confirmation={
          creationConfirmOpen && draft.createdDocId ? (
            <>
              <p className="elf-cmp-focus__confirmation-title">
                {docSent
                  ? `Document ${draft.createdDocNumber ?? ''} envoyé`
                  : `Document ${draft.createdDocNumber ?? ''} enregistré`}
              </p>
              <div className="elf-cmp-focus__confirmation-actions">
                <button
                  type="button"
                  className="elf-cmp-action elf-cmp-action--primary"
                  onClick={() =>
                    exitToDocuments({ docId: draft.createdDocId })
                  }
                >
                  Ouvrir le document
                </button>
                {draft.createdDocId && !docSent ? (
                  <button
                    type="button"
                    className="elf-cmp-action elf-cmp-action--secondary"
                    onClick={() => void sendDoc()}
                  >
                    Envoyer
                  </button>
                ) : null}
                <button
                  type="button"
                  className="elf-cmp-action elf-cmp-action--secondary"
                  onClick={() => exitToDocuments({ docId: draft.createdDocId })}
                >
                  Revenir aux Documents
                </button>
                <button
                  type="button"
                  className="elf-cmp-action elf-cmp-action--ghost"
                  onClick={() => {
                    setCreationConfirmOpen(false)
                    exitToDocuments({ reopenCreate: true })
                  }}
                >
                  Créer un autre
                </button>
              </div>
            </>
          ) : null
        }
        footer={guidedFooter}
      >
        {isModal ? guidedBody : freeformBody}
      </ComposerFocusLayout>

      <ExitConfirmationDialog
        open={exitConfirmOpen}
        onOpenChange={(open) => {
          if (!open) setExitSaveError('')
          setExitConfirmOpen(open)
        }}
        docType={draft.docType}
        busy={busy}
        saveError={exitSaveError}
        onContinue={() => {
          setExitSaveError('')
          setExitConfirmOpen(false)
        }}
        onDiscard={() => {
          setExitSaveError('')
          setExitConfirmOpen(false)
          exitToDocuments()
        }}
        onSaveAndQuit={() => void saveAndClose()}
      />
    </div>
  )
}
