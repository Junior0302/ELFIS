import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { useSync } from '../sync/SyncProvider'
import { getWorkspaceByProductId } from '../workspaces'
import {
  ContinueWorkCard,
  buildContinueItemsFromRegistry,
} from './ContinueWorkCard'
import { CockpitHero } from './CockpitHero'
import { SpacesSection } from './SpacesSection'
import { GlobalTimeline } from './GlobalTimeline'
import { ElfisIntelligenceCard } from './ElfisIntelligenceCard'
import { QuickActionsGrid } from './QuickActionsGrid'
import { HealthCenter } from './HealthCenter'
import { PlatformHomeSection } from './PlatformHomeSection'
import { PlatformWatchItem } from './PlatformWatchItem'
import { PlatformOrgContext } from './PlatformOrgContext'
import { getLastProductAt, getLastProductId } from './lastProduct'
import {
  buildDetectionSignals,
  buildHealthLamps,
  buildWatchItems,
  platformStatusLabel,
  relativeCheckLabel,
} from './homeSignals'
import {
  ElfisDashboardTemplate,
  MotionPage,
  isUnifiedPlatformUiEnabled,
} from '../unified-platform'
import './home.css'
import './platform-home.css'

function formatLastSeen(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return '—'
  }
}

function historyRouteFor(productId: string | undefined): string | null {
  if (productId === 'comptapilot') return '/history'
  if (productId === 'salespilot') return '/sales/journal'
  return null
}

function greetingForNow(now = new Date()): string {
  const h = now.getHours()
  if (h < 18) return 'Bonjour'
  return 'Bonsoir'
}

function dateLabelForNow(now = new Date()): string {
  return now.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

/**
 * Accueil plateforme ELFIS — cockpit OS premium.
 * Pas de duplication des dashboards métier.
 */
export default function ElfisHomePage() {
  const { user, memberships, orgId, token } = useAuth()
  const { unreadNotifications, lastTickAt, mode } = useSync()
  const firstName = user?.first_name?.trim() || 'vous'
  const org = memberships.find((m) => m.organization_id === orgId) ?? memberships[0]
  const orgName = org?.organization_name ?? '—'
  const orgRole = org?.role
  const lastId = getLastProductId()
  const lastAt = getLastProductAt()
  const unified = isUnifiedPlatformUiEnabled()
  const connected = Boolean(token && user)
  const orgOk = Boolean(orgId != null && orgName && orgName !== '—')
  const syncOk = Boolean(token && orgId != null)
  const unreadKnown = Boolean(token && orgId != null)

  const signals = useMemo(
    () =>
      buildDetectionSignals({
        connected,
        orgName,
        orgOk,
        unreadNotifications: unreadKnown ? unreadNotifications : 0,
        syncOk,
        lastProductId: lastId,
      }),
    [connected, orgName, orgOk, unreadNotifications, unreadKnown, syncOk, lastId],
  )

  const watchItems = useMemo(() => buildWatchItems(signals), [signals])

  const healthLamps = useMemo(
    () =>
      buildHealthLamps({
        connected,
        orgOk,
        syncOk,
        syncMode: mode,
        unreadKnown,
      }),
    [connected, orgOk, syncOk, mode, unreadKnown],
  )

  const continueItems = useMemo(
    () => buildContinueItemsFromRegistry(lastId, lastAt, formatLastSeen, historyRouteFor),
    [lastId, lastAt],
  )

  const lastWorkspace = getWorkspaceByProductId(lastId)
  const healthOk = healthLamps
    .filter((l) => l.id === 'connection' || l.id === 'org' || l.id === 'sync')
    .every((l) => l.tone === 'green')
  const healthLabel = platformStatusLabel(healthOk)
  const lastCheck = relativeCheckLabel(
    lastTickAt.notifications || (mode ? new Date().toISOString() : undefined),
  )
  const attentionCount = signals.filter((s) => s.tone === 'attention').length

  const hero = (
    <CockpitHero
      firstName={firstName}
      orgName={orgName}
      healthLabel={healthLabel}
      healthOk={healthOk}
      signals={signals}
      dateLabel={dateLabelForNow()}
      greeting={greetingForNow()}
    />
  )

  /** Bande métriques plateforme (pas de KPI métier inventés). */
  const metrics = (
    <div className="up-dash-band up-dash-band--metrics ph-metrics-band">
      <ul className="ph-metrics" aria-label="Signaux plateforme">
        <li>
          <span className="ph-metrics__label">Organisation</span>
          <strong className="ph-metrics__value">{orgOk ? orgName : 'À configurer'}</strong>
        </li>
        <li>
          <span className="ph-metrics__label">À traiter</span>
          <strong className="ph-metrics__value">{attentionCount}</strong>
        </li>
        <li>
          <span className="ph-metrics__label">Notifications</span>
          <strong className="ph-metrics__value">
            {unreadKnown ? unreadNotifications : '—'}
          </strong>
        </li>
        <li>
          <span className="ph-metrics__label">État</span>
          <strong className="ph-metrics__value">{healthLabel}</strong>
        </li>
      </ul>
    </div>
  )

  const watchSection = (
    <PlatformHomeSection
      id="home-watch"
      title="À surveiller"
      description="Éléments actionnables uniquement."
      level={1}
      className="ph-watch"
    >
      {watchItems.length === 0 ? (
        <p className="ph-empty-compact" role="status">
          Aucune action prioritaire.
        </p>
      ) : (
        <ul className="ph-watch__list">
          {watchItems.map((item) => (
            <li key={item.id}>
              <PlatformWatchItem
                id={item.id}
                title={item.title}
                context={item.context}
                href={item.href}
                tone={item.tone}
              />
            </li>
          ))}
        </ul>
      )}
    </PlatformHomeSection>
  )

  const primary = (
    <div
      className="up-dash-band up-dash-band--primary cockpit-primary ph-home"
      data-home-layout="platform-home-v4"
      data-ph-home="v4"
    >
      <div className="ph-home__row ph-home__row--priority">
        <ContinueWorkCard items={continueItems} />
        {watchSection}
      </div>

      <SpacesSection lastProductId={lastId} lastProductAt={lastAt} />

      <div className="ph-home__row ph-home__row--tools">
        <ElfisIntelligenceCard
          signals={signals}
          unreadNotifications={unreadKnown ? unreadNotifications : 0}
          embedded
        />
        <QuickActionsGrid embedded />
      </div>

      <GlobalTimeline
        embedded
        lastProductLabel={lastWorkspace?.label ?? null}
        lastProductAt={lastAt}
        lastProductTo={lastWorkspace?.rootPath ?? null}
        lastProductAccent={lastWorkspace?.accent.primary ?? null}
        syncTickAt={lastTickAt.notifications}
        syncMode={mode}
      />
    </div>
  )

  const secondary = (
    <div className="up-dash-band up-dash-band--secondary cockpit-secondary ph-home-rail">
      <HealthCenter
        embedded
        lamps={healthLamps}
        lastCheckLabel={lastCheck}
        allOk={healthOk}
      />
      <PlatformOrgContext
        orgName={orgName}
        orgRole={orgRole}
        memberCount={memberships.length}
        connected={connected}
      />
    </div>
  )

  const operations = (
    <nav className="cockpit-ops cockpit-ops--v4" aria-label="Raccourcis plateforme">
      <span className="cockpit-ops__label">OS</span>
      <Link to="/platform/organization">Organisation</Link>
      <Link to="/platform/documents">Documents</Link>
      <Link to="/platform/settings">Paramètres</Link>
      <Link to="/notifications">Notifications</Link>
    </nav>
  )

  if (unified) {
    return (
      <MotionPage className="cockpit-os cockpit-os--signature ph-shell">
        <div data-cockpit-os="platform-home-v4" data-ph-home-root="v4">
          <ElfisDashboardTemplate
            dashboardId="home"
            header={
              <>
                <h1 className="elfis-home__sr-only">Cockpit ELFIS</h1>
                {hero}
              </>
            }
            metrics={metrics}
            primaryAnalysis={primary}
            secondaryAnalysis={secondary}
            operations={operations}
          />
        </div>
      </MotionPage>
    )
  }

  return (
    <div
      className="elfis-home elfis-home--hybrid cockpit-os cockpit-os--signature ph-shell"
      data-home="platform-home-v4"
      data-cockpit-os="platform-home-v4"
      data-unified-home="0"
    >
      {hero}
      {metrics}
      {primary}
      {secondary}
      {operations}
    </div>
  )
}
