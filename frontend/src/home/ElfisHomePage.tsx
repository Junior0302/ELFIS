import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { useSync } from '../sync/SyncProvider'
import { HOME_APP_CARDS } from './homeCatalog'
import { ContinueWorkCard, type ContinueWorkItem } from './ContinueWorkCard'
import { CockpitHero } from './CockpitHero'
import { DaySummarySection } from './DaySummarySection'
import { SpacesSection } from './SpacesSection'
import { GlobalTimeline } from './GlobalTimeline'
import { ElfisIntelligenceCard } from './ElfisIntelligenceCard'
import { QuickActionsGrid } from './QuickActionsGrid'
import { HealthCenter } from './HealthCenter'
import { getLastProductAt, getLastProductId } from './lastProduct'
import {
  buildDayDomainCards,
  buildDetectionSignals,
  buildHealthLamps,
  relativeCheckLabel,
} from './homeSignals'
import {
  ElfisDashboardTemplate,
  MotionPage,
  isUnifiedPlatformUiEnabled,
} from '../unified-platform'
import './home.css'

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

function buildContinueItems(
  lastId: string | null,
  lastAt: string | null,
): ContinueWorkItem[] {
  if (!lastId || !lastAt) return []
  const primary =
    HOME_APP_CARDS.find((a) => a.id === lastId && a.available && a.to) ??
    HOME_APP_CARDS.find((a) => a.available && a.to)
  if (!primary?.to) return []

  return [
    {
      id: `resume-${primary.id}`,
      letter: primary.name.charAt(0).toUpperCase(),
      accent: primary.accent,
      title: primary.id === 'comptapilot' ? 'Finance' : primary.id === 'salespilot' ? 'Commercial' : primary.name,
      meta: `Dernière session · ${primary.description}`,
      status: 'En cours',
      statusTone: 'neutral',
      timeLabel: formatLastSeen(lastAt),
      to: primary.to,
      historyTo: historyRouteFor(primary.productId),
      productId: primary.productId,
    },
  ]
}

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

  const dayCards = useMemo(
    () =>
      buildDayDomainCards({
        orgName,
        orgRole,
        lastProductId: lastId,
        lastProductAt: lastAt,
        unreadNotifications: unreadKnown ? unreadNotifications : 0,
      }),
    [orgName, orgRole, lastId, lastAt, unreadNotifications, unreadKnown],
  )

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
    () => buildContinueItems(lastId, lastAt),
    [lastId, lastAt],
  )

  const emptyActions = useMemo(
    () =>
      HOME_APP_CARDS.filter((a) => a.available && a.to).map((a) => ({
        label: a.id === 'comptapilot' ? 'Ouvrir Finance' : a.id === 'salespilot' ? 'Ouvrir Commercial' : `Ouvrir ${a.name}`,
        to: a.to!,
        productId: a.productId,
        accent: a.accent,
      })),
    [],
  )

  const lastProductCard = HOME_APP_CARDS.find((a) => a.id === lastId)
  const healthOk = healthLamps.every((l) => l.tone === 'green')
  const healthLabel = healthOk ? 'Santé plateforme OK' : 'Attention requise'
  const lastCheck = relativeCheckLabel(
    lastTickAt.notifications || (mode ? new Date().toISOString() : undefined),
  )

  const hero = (
    <CockpitHero
      firstName={firstName}
      orgName={orgName}
      healthLabel={healthLabel}
      healthOk={healthOk}
      signals={signals}
    />
  )

  /** Glance domaines — bande mince sous le hero. */
  const dayBand = (
    <div className="up-dash-band up-dash-band--metrics cockpit-band cockpit-band--pulse cockpit-band--v3">
      <DaySummarySection cards={dayCards} />
    </div>
  )

  /**
   * Hiérarchie V3 : Command (conseil + gestes) → Continuer → Espaces.
   * Pas de stack de panels ; peu d’excellentes surfaces.
   */
  const primary = (
    <div
      className="up-dash-band up-dash-band--primary cockpit-primary"
      data-home-layout="cockpit-signature-v3"
    >
      <div className="cockpit-command cockpit-command--signature" data-cockpit-command="v3">
        <ElfisIntelligenceCard
          signals={signals}
          unreadNotifications={unreadKnown ? unreadNotifications : 0}
          embedded
        />
        <QuickActionsGrid embedded />
      </div>
      <ContinueWorkCard items={continueItems} emptyActions={emptyActions} />
      <SpacesSection lastProductId={lastId} lastProductAt={lastAt} />
    </div>
  )

  const secondary = (
    <div className="up-dash-band up-dash-band--secondary cockpit-secondary cockpit-system-rail cockpit-system-rail--v3">
      <GlobalTimeline
        embedded
        lastProductLabel={
          lastProductCard
            ? lastProductCard.id === 'comptapilot'
              ? 'Espace Finance'
              : lastProductCard.id === 'salespilot'
                ? 'Espace Commercial'
                : lastProductCard.name
            : null
        }
        lastProductAt={lastAt}
        lastProductTo={lastProductCard?.to ?? null}
        syncTickAt={lastTickAt.notifications}
        syncMode={mode}
      />
      <HealthCenter embedded lamps={healthLamps} lastCheckLabel={lastCheck} allOk={healthOk} />
    </div>
  )

  const operations = (
    <nav className="cockpit-ops cockpit-ops--v3" aria-label="Raccourcis plateforme">
      <span className="cockpit-ops__label">OS</span>
      <Link to="/platform/organization">Organisation</Link>
      <Link to="/platform/documents">Documents</Link>
      <Link to="/platform/settings">Paramètres</Link>
      <Link to="/notifications">Notifications</Link>
    </nav>
  )

  if (unified) {
    return (
      <MotionPage className="cockpit-os cockpit-os--signature">
        <div data-cockpit-os="signature-v3">
          <ElfisDashboardTemplate
            dashboardId="home"
            header={
              <>
                <h1 className="elfis-home__sr-only">Cockpit ELFIS</h1>
                {hero}
              </>
            }
            metrics={dayBand}
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
      className="elfis-home elfis-home--hybrid cockpit-os cockpit-os--signature"
      data-home="cockpit-signature-v3"
      data-cockpit-os="signature-v3"
      data-unified-home="0"
    >
      {hero}
      {dayBand}
      {primary}
      {secondary}
      {operations}
    </div>
  )
}
