/**
 * Isolated Theme Engine sandbox (dev only).
 * Neutral examples — no business components.
 */

import {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react'
import { Navigate } from 'react-router-dom'
import { PRODUCT_REGISTRY } from '../products/registry'
import { applyProductTheme } from '../themes/applyProductTheme'
import { THEME_DOM_ATTR } from '../themes/cssVariables'
import { ProductThemeProvider, useProductTheme } from '../themes/ProductThemeProvider'
import {
  DESIGN_SYSTEM_THEME_SANDBOX_PATH,
  isDesignSystemSandboxEnabled,
} from './isDesignSystemSandboxEnabled'
import {
  Badge,
  Button,
  Container,
  Grid,
  Inline,
  MetricCard,
  QuickActionCard,
  Section,
  Stack,
  StatCard,
} from '../components'
import {
  ConfirmDialog,
  Dialog,
  Drawer,
  Popover,
  Tooltip,
} from '../overlays'
import { useOverlayStackDebug } from '../overlays/hooks/useOverlayManager'
import { AppLauncher } from '../../app-launcher/AppLauncher'
import '../components/components.css'
import './themeSandbox.css'

function SandboxDomBridge({
  target,
  children,
}: {
  target: HTMLElement
  children: ReactNode
}) {
  const { currentTheme } = useProductTheme()
  useEffect(() => applyProductTheme(currentTheme, target), [currentTheme, target])
  return <>{children}</>
}

function SandboxBoard() {
  const {
    currentProductId,
    currentTheme,
    setCurrentProduct,
    availableProducts,
    error,
    mode,
  } = useProductTheme()

  const tokens = currentTheme.tokens
  const gradientStyle: CSSProperties = {
    background: `linear-gradient(135deg, ${tokens.gradientStart}, ${tokens.gradientEnd})`,
  }

  return (
    <div className="ds-theme-sandbox" data-testid="ds-theme-sandbox">
      <header className="ds-theme-sandbox__header">
        <p className="ds-theme-sandbox__eyebrow">ELFIS Design System · Theme Engine V1</p>
        <h1>Theme Sandbox</h1>
        <p className="ds-theme-sandbox__lede">
          Prévisualisation isolée des tokens <code>--pilot-*</code>. Aucun écran métier.
        </p>
      </header>

      <label className="ds-theme-sandbox__field" htmlFor="ds-product-select">
        Produit à prévisualiser
        <select
          id="ds-product-select"
          value={currentProductId}
          onChange={(e) => setCurrentProduct(e.target.value)}
          aria-describedby="ds-product-status"
        >
          {availableProducts.map((p) => (
            <option key={p.id} value={p.id}>
              {p.displayName} ({p.status})
            </option>
          ))}
        </select>
      </label>

      <p id="ds-product-status" className="ds-theme-sandbox__status" role="status" aria-live="polite">
        Produit actif : <strong>{currentTheme.branding.displayName}</strong> · statut{' '}
        {currentTheme.metadata.status} · catégorie {currentTheme.metadata.category} · mode {mode}
        {error ? ` · erreur : ${error}` : ''}
      </p>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-meta-title">
        <h2 id="ds-meta-title">Identité</h2>
        <dl className="ds-theme-sandbox__dl">
          <div>
            <dt>Nom</dt>
            <dd>{currentTheme.branding.displayName}</dd>
          </div>
          <div>
            <dt>Short</dt>
            <dd>{currentTheme.branding.shortName}</dd>
          </div>
          <div>
            <dt>Primary</dt>
            <dd>
              <span
                className="ds-theme-sandbox__swatch"
                style={{ background: 'var(--pilot-primary)' }}
                aria-hidden
              />
              {tokens.primary}
            </dd>
          </div>
          <div>
            <dt>Tagline</dt>
            <dd>{currentTheme.metadata.tagline}</dd>
          </div>
        </dl>
      </section>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-grad-title">
        <h2 id="ds-grad-title">Gradient</h2>
        <div
          className="ds-theme-sandbox__gradient"
          style={gradientStyle}
          role="img"
          aria-label={`Gradient ${tokens.gradientStart} vers ${tokens.gradientEnd}`}
        />
        <p>
          {tokens.gradientStart} → {tokens.gradientEnd}
        </p>
      </section>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-examples-title">
        <h2 id="ds-examples-title">Exemples neutres</h2>
        <div className="ds-theme-sandbox__examples">
          <button type="button" className="ds-theme-sandbox__btn">
            Bouton Pilot
          </button>
          <div className="ds-theme-sandbox__card">
            <h3>Carte exemple</h3>
            <p>Surface et texte pilotés uniquement par les variables CSS Pilot.</p>
          </div>
          <span className="ds-theme-sandbox__badge">Badge</span>
          <a href="#focus-demo" className="ds-theme-sandbox__focus-link" id="focus-demo">
            Lien focus visible
          </a>
        </div>
      </section>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-chart-title">
        <h2 id="ds-chart-title">Mini palette graphique</h2>
        <ul className="ds-theme-sandbox__charts">
          {(
            [
              ['chart1', tokens.chart1],
              ['chart2', tokens.chart2],
              ['chart3', tokens.chart3],
              ['chart4', tokens.chart4],
              ['chart5', tokens.chart5],
              ['chart6', tokens.chart6],
              ['chart7', tokens.chart7],
              ['chart8', tokens.chart8],
            ] as const
          ).map(([name, color]) => (
            <li key={name}>
              <span style={{ background: `var(--pilot-${name.replace('chart', 'chart-')})` }} aria-hidden />
              <span>
                {name}: {color}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-tokens-title">
        <h2 id="ds-tokens-title">Tokens</h2>
        <ul className="ds-theme-sandbox__token-list">
          {Object.entries(tokens).map(([key, value]) => (
            <li key={key}>
              <span
                className="ds-theme-sandbox__swatch"
                style={{ background: value }}
                aria-hidden
              />
              <code>{key}</code>
              <span>{value}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-components-title">
        <h2 id="ds-components-title">Component System V1</h2>
        <p className="ds-theme-sandbox__hint">
          Comparatif accent Pilot : ComptaPilot / SalesPilot / DocPilot via le sélecteur. Success /
          warning / danger restent fixes.
        </p>
        <Stack gap={6}>
          <Section
            title="Section exemple"
            description="Structure de bloc uniforme"
            eyebrow="Structure"
            actions={<Button size="sm">Action</Button>}
            variant="bordered"
          >
            <Inline gap={2} wrap>
              <Badge tone="accent">Accent Pilot</Badge>
              <Badge tone="ok">Success fixe</Badge>
              <Badge tone="warn">Warning fixe</Badge>
              <Badge tone="danger">Danger fixe</Badge>
            </Inline>
          </Section>

          <Grid columns={2} gap={4} responsive>
            <StatCard
              label="Indicateur"
              value="128"
              description="Synthétique"
              variant="accent"
              trend={{
                value: '−4 %',
                direction: 'down',
                label: 'vs mois dernier',
                sentiment: 'positive',
              }}
            />
            <MetricCard
              title="Métrique enrichie"
              value="92 %"
              subtitle="Sans calcul métier"
              progress={92}
              supportingText="Le progress est fourni par l’appelant."
              footer="Footer neutre"
              variant="accent"
              status={<Badge tone="accent">Pilot</Badge>}
            />
          </Grid>

          <Container size="md" padding="none">
            <QuickActionCard
              title="Action rapide"
              description="Lien ou bouton — jamais un div cliquable"
              href="#quick-action-demo"
              accent
              badge={<Badge tone="accent">New</Badge>}
            />
          </Container>

          <div>
            <p className="ds-theme-sandbox__hint">Tokens fondation</p>
            <ul className="ds-theme-sandbox__token-list">
              <li>
                <code>--space-4</code>
                <span>gap Stack / Grid</span>
              </li>
              <li>
                <code>--radius-lg</code>
                <span>cartes</span>
              </li>
              <li>
                <code>--shadow-sm</code>
                <span>élévation légère</span>
              </li>
              <li>
                <code>--motion-duration-fast</code>
                <span>hover / focus</span>
              </li>
              <li>
                <code>--container-md</code>
                <span>largeur contenue</span>
              </li>
            </ul>
          </div>
        </Stack>
      </section>

      <OverlaySandboxDemos />

      <AppLauncherSandboxDemos />

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-brand-title">
        <h2 id="ds-brand-title">Branding paths</h2>
        <ul>
          <li>logo: {currentTheme.branding.logo}</li>
          <li>logoMark: {currentTheme.branding.logoMark}</li>
          <li>favicon: {currentTheme.branding.favicon}</li>
          <li>illustrations: {currentTheme.branding.illustrations}</li>
        </ul>
      </section>

      <section className="ds-theme-sandbox__section" aria-labelledby="ds-attrs-title">
        <h2 id="ds-attrs-title">Data attributes (cible sandbox)</h2>
        <p>
          {THEME_DOM_ATTR.product}=&quot;{currentProductId}&quot; · {THEME_DOM_ATTR.theme}=&quot;
          {currentProductId}-light&quot; · {THEME_DOM_ATTR.colorScheme}=&quot;light&quot;
        </p>
        <p className="ds-theme-sandbox__hint">
          Produits registry : {PRODUCT_REGISTRY.length} · sélecteur : {availableProducts.length}
        </p>
      </section>
    </div>
  )
}

function OverlaySandboxDemos() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [confirmTone, setConfirmTone] = useState<'neutral' | 'warning' | 'danger' | null>(null)
  const [drawerSide, setDrawerSide] = useState<'right' | 'bottom' | null>(null)
  const [nestedOuter, setNestedOuter] = useState(false)
  const [nestedInner, setNestedInner] = useState(false)
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [scrollOpen, setScrollOpen] = useState(false)
  const { snapshot, depth } = useOverlayStackDebug()

  return (
    <section className="ds-theme-sandbox__section" aria-labelledby="ds-overlays-title">
      <h2 id="ds-overlays-title">Overlay System V1</h2>
      <p className="ds-theme-sandbox__hint">
        Dialog · Confirm · Drawer · Tooltip · Popover — accents Pilot via le sélecteur. Reduced
        motion : OS / préférence navigateur.
      </p>
      {import.meta.env.DEV ? (
        <div className="ds-theme-sandbox__hint" data-testid="overlay-stack-debug">
          <strong>Overlay stack</strong> (depth {depth})
          <ol>
            {snapshot.length === 0 ? (
              <li>vide</li>
            ) : (
              snapshot.map((s) => (
                <li key={s.id}>
                  {s.id} · {s.type} · {s.priority}
                  {s.isTop ? ' · TOP' : ''} · modal={String(s.modal)} · dismissible=
                  {String(s.dismissible)}
                </li>
              ))
            )}
          </ol>
        </div>
      ) : null}
      <Stack gap={4}>
        <Inline gap={2} wrap>
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            Dialog simple
          </Button>
          <Button size="sm" onClick={() => setFormOpen(true)}>
            Dialog formulaire
          </Button>
          <Button size="sm" onClick={() => setConfirmTone('neutral')}>
            Confirm neutral
          </Button>
          <Button size="sm" onClick={() => setConfirmTone('warning')}>
            Confirm warning
          </Button>
          <Button size="sm" onClick={() => setConfirmTone('danger')}>
            Confirm danger
          </Button>
          <Button size="sm" onClick={() => setDrawerSide('right')}>
            Drawer right
          </Button>
          <Button size="sm" onClick={() => setDrawerSide('bottom')}>
            Drawer bottom
          </Button>
          <Button size="sm" onClick={() => setNestedOuter(true)}>
            Overlays imbriqués
          </Button>
          <Button size="sm" onClick={() => setScrollOpen(true)}>
            Scroll long
          </Button>
          <Tooltip content="Info accessible au focus et au hover" placement="top">
            <Button size="sm" variant="secondary">
              Tooltip
            </Button>
          </Tooltip>
          <Popover
            open={popoverOpen}
            onOpenChange={setPopoverOpen}
            trigger={
              <Button size="sm" variant="secondary">
                Popover
              </Button>
            }
          >
            <p>Panneau léger non modal.</p>
            <Button size="sm" onClick={() => setPopoverOpen(false)}>
              Fermer
            </Button>
          </Popover>
        </Inline>
      </Stack>

      <Dialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Dialog simple"
        description="Exemple neutre Overlay System V1."
        footer={
          <Button size="sm" onClick={() => setDialogOpen(false)}>
            OK
          </Button>
        }
      >
        <p>Contenu dialog — tokens surfaces + accent Pilot.</p>
      </Dialog>

      <Dialog
        open={formOpen}
        onOpenChange={setFormOpen}
        title="Dialog formulaire"
        description="Champs neutres, sans métier."
        footer={
          <Inline gap={2}>
            <Button size="sm" variant="secondary" onClick={() => setFormOpen(false)}>
              Annuler
            </Button>
            <Button size="sm" onClick={() => setFormOpen(false)}>
              Enregistrer
            </Button>
          </Inline>
        }
      >
        <Stack gap={3}>
          <label>
            Libellé
            <input className="ds-input" type="text" placeholder="Valeur" />
          </label>
          <label>
            Notes
            <textarea className="ds-input" rows={3} placeholder="Texte" />
          </label>
        </Stack>
      </Dialog>

      <ConfirmDialog
        open={confirmTone !== null}
        onOpenChange={(o) => {
          if (!o) setConfirmTone(null)
        }}
        title={
          confirmTone === 'danger'
            ? 'Action destructive'
            : confirmTone === 'warning'
              ? 'Action sensible'
              : 'Confirmer'
        }
        description="Exemple ConfirmDialog — libellés fournis par l’appelant."
        tone={confirmTone ?? 'neutral'}
        confirmLabel="Confirmer"
        cancelLabel="Annuler"
        onConfirm={() => setConfirmTone(null)}
      />

      <Drawer
        open={drawerSide !== null}
        onOpenChange={(o) => {
          if (!o) setDrawerSide(null)
        }}
        side={drawerSide ?? 'right'}
        title="Drawer démo"
        description={drawerSide === 'bottom' ? 'Bottom sheet' : 'Panneau latéral'}
      >
        <p>Contenu drawer scrollable. Header/footer fixes via structure DS.</p>
      </Drawer>

      <Dialog
        open={nestedOuter}
        onOpenChange={setNestedOuter}
        title="Overlay parent"
        description="Escape ferme d’abord l’enfant."
        footer={
          <Button size="sm" onClick={() => setNestedInner(true)}>
            Ouvrir enfant
          </Button>
        }
      >
        <p>Parent ouvert.</p>
      </Dialog>
      <Dialog
        open={nestedInner}
        onOpenChange={setNestedInner}
        title="Overlay enfant"
        description="Top overlay prioritaire."
        size="sm"
      >
        <p>Enfant — Escape ferme uniquement celui-ci.</p>
      </Dialog>

      <Dialog
        open={scrollOpen}
        onOpenChange={setScrollOpen}
        title="Scroll long"
        description="Le panel scrolle ; header/footer restent accessibles."
        size="lg"
        footer={
          <Button size="sm" onClick={() => setScrollOpen(false)}>
            Fermer
          </Button>
        }
      >
        <Stack gap={3}>
          {Array.from({ length: 24 }, (_, i) => (
            <p key={i}>Ligne de contenu {i + 1} — vérifie le scroll interne.</p>
          ))}
        </Stack>
      </Dialog>
    </section>
  )
}

function AppLauncherSandboxDemos() {
  const [preview, setPreview] = useState(false)

  return (
    <section className="ds-theme-sandbox__section" aria-labelledby="ds-launcher-title">
      <h2 id="ds-launcher-title">App Launcher V1</h2>
      <p className="ds-theme-sandbox__hint">
        Mode réel : ComptaPilot actif, Sales/Doc coming_soon. Mode preview : overrides isolés — le
        Product Registry n’est jamais muté.
      </p>
      <Stack gap={3}>
        <Inline gap={2} wrap>
          <Button size="sm" variant={preview ? 'secondary' : 'primary'} onClick={() => setPreview(false)}>
            État réel V1
          </Button>
          <Button size="sm" variant={preview ? 'primary' : 'secondary'} onClick={() => setPreview(true)}>
            Preview Design System
          </Button>
        </Inline>
        <AppLauncher
          mode={preview ? 'sandbox_preview' : 'production'}
          previewOverrides={
            preview
              ? {
                  salespilot: { state: 'available', route: '/dashboard', canOpen: true },
                  docpilot: { state: 'beta', route: '/dashboard', canOpen: true },
                  hrpilot: { state: 'locked' },
                }
              : undefined
          }
        />
        <p className="ds-theme-sandbox__hint">
          En preview, SalesPilot/DocPilot sont simulés ouvrables vers /dashboard (dev only) — pas de
          routes métier inventées en production.
        </p>
      </Stack>
    </section>
  )
}

function SandboxHost() {
  const [host, setHost] = useState<HTMLDivElement | null>(null)
  const setRef = useCallback((node: HTMLDivElement | null) => {
    setHost(node)
  }, [])

  return (
    <div ref={setRef} className="ds-theme-sandbox-host">
      {host ? (
        <ProductThemeProvider
          initialProductId="comptapilot"
          allowPreviewUnavailableProducts
          persist={false}
          applyToDom={false}
        >
          <SandboxDomBridge target={host}>
            <SandboxBoard />
          </SandboxDomBridge>
        </ProductThemeProvider>
      ) : null}
    </div>
  )
}

export default function ThemeSandboxPage() {
  if (!isDesignSystemSandboxEnabled()) {
    return <Navigate to="/" replace />
  }
  return <SandboxHost />
}

export { DESIGN_SYSTEM_THEME_SANDBOX_PATH }
