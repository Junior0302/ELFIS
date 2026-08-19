import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'

import { useNavigate } from 'react-router-dom'

import { useProductTheme } from '../design-system/themes/ProductThemeProvider'

import { closeAllOverlays } from '../design-system/overlays/manager/overlayLifecycle'

import { Dialog } from '../design-system/overlays/Dialog'

import { Drawer } from '../design-system/overlays/Drawer'

import { trackProductEvent } from '../productEvents'

import { closeChromeMenus } from '../platform-shell/global-nav/chromeMenus'

import type { AppLauncherMode, LauncherResolveContext } from './launcher.types'

import type { ResolvedSpace } from './spaces.types'

import { buildSpaceSections, resolveSpaceState } from './spacesModel'

import { getKnownSpaRoutes } from './productEntryRoutes'

import { AppLauncherPanel } from './AppLauncherPanel'

import { AppLauncherTrigger } from './AppLauncherTrigger'

import { setLastProductId } from '../home/lastProduct'

import type { ProductId } from '../design-system/types'

import './launcher.css'



const MOBILE_MQ = '(max-width: 1024px)'



const TITLE = 'Espaces ELFIS'

const DESCRIPTION = 'Accédez à tous les métiers de votre entreprise depuis un seul espace.'



function useIsMobileLauncher(): boolean {

  const [mobile, setMobile] = useState(() =>

    typeof window !== 'undefined' ? window.matchMedia(MOBILE_MQ).matches : false,

  )

  useEffect(() => {

    if (typeof window === 'undefined') return

    const mq = window.matchMedia(MOBILE_MQ)

    const onChange = () => setMobile(mq.matches)

    onChange()

    mq.addEventListener('change', onChange)

    return () => mq.removeEventListener('change', onChange)

  }, [])

  return mobile

}



export type AppLauncherProps = {

  mode?: AppLauncherMode

  /** Sandbox-only overrides — never mutates Product Registry. */

  previewOverrides?: LauncherResolveContext['previewOverrides']

  className?: string

  compactTrigger?: boolean

}



/**

 * Hub Espaces ELFIS — panel signature (BRAND.ELFIS.1).

 * Desktop: Dialog centré · Mobile: Drawer bottom.

 * Never calls setCurrentProduct() / applyTheme() — route is source of truth.

 */

export function AppLauncher({

  mode = 'production',

  previewOverrides,

  className,

  compactTrigger,

}: AppLauncherProps) {

  const [open, setOpen] = useState(false)

  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const [resolveFailed, setResolveFailed] = useState(false)

  const panelId = useId()

  const isMobile = useIsMobileLauncher()

  const navigate = useNavigate()

  const { currentProductId } = useProductTheme()

  const previewMode = mode === 'sandbox_preview'

  const triggerRef = useRef<HTMLButtonElement>(null)

  const searchInputRef = useRef<HTMLInputElement>(null)



  const context = useMemo<LauncherResolveContext>(

    () => ({

      currentProductId,

      availableRoutes: getKnownSpaRoutes(),

      previewOverrides: previewMode ? previewOverrides : undefined,

      previewMode,

    }),

    [currentProductId, previewOverrides, previewMode],

  )



  const sections = useMemo(() => {

    try {

      const built = buildSpaceSections(context)

      return { built, ok: true as const }

    } catch {

      return {

        built: { available: [], comingSoon: [] },

        ok: false as const,

      }

    }

  }, [context])



  useEffect(() => {

    if (!sections.ok) {

      setResolveFailed(true)

      setErrorMessage('Impossible de charger les espaces. Finance reste accessible.')

    } else if (resolveFailed) {

      setResolveFailed(false)

      setErrorMessage(null)

    }

  }, [sections.ok, resolveFailed])



  const trackOpenClose = useCallback(

    (next: boolean) => {

      try {

        trackProductEvent(next ? 'app_launcher.opened' : 'app_launcher.closed', {

          currentProductId,

          source: previewMode ? 'sandbox' : 'workspace',

          viewport: isMobile ? 'mobile' : 'desktop',

        })

      } catch {

        /* analytics must never block */

      }

    },

    [currentProductId, previewMode, isMobile],

  )



  const onOpenChange = useCallback(

    (next: boolean) => {

      if (next) {

        closeAllOverlays('programmatic')

        closeChromeMenus()

      }

      setOpen(next)

      trackOpenClose(next)

      if (!next) setErrorMessage(null)

    },

    [trackOpenClose],

  )



  const handleUnavailable = useCallback(

    (item: ResolvedSpace) => {

      try {

        trackProductEvent('app_launcher.unavailable_clicked', {

          currentProductId,

          selectedProductId: item.space.engineProductId ?? item.space.id,

          state: item.state,

        })

      } catch {

        /* ignore */

      }

      if (item.state === 'coming_soon') return

      setErrorMessage(item.reason || 'Cet espace n’est pas encore disponible.')

    },

    [currentProductId],

  )



  const handleSelect = useCallback(

    (item: ResolvedSpace) => {

      if (item.state === 'active' && item.route) {

        onOpenChange(false)

        return

      }

      if (!item.canOpen || !item.route) {

        handleUnavailable(item)

        return

      }



      const fresh = resolveSpaceState(item.space, context)

      if (!fresh.canOpen || !fresh.route) {

        setErrorMessage('Cet espace n’est plus disponible.')

        return

      }



      try {

        trackProductEvent('app_launcher.product_selected', {

          currentProductId,

          selectedProductId: item.space.engineProductId ?? item.space.id,

          source: previewMode ? 'sandbox' : 'workspace',

          viewport: isMobile ? 'mobile' : 'desktop',

        })

      } catch {

        /* ignore */

      }



      closeAllOverlays('product_change')

      const pid = item.space.engineProductId

      if (pid === 'comptapilot' || pid === 'salespilot') {

        setLastProductId(pid as ProductId)

      }

      onOpenChange(false)

      navigate(fresh.route)

    },

    [context, currentProductId, handleUnavailable, isMobile, navigate, onOpenChange, previewMode],

  )



  /* Cmd/Ctrl+Shift+A — do not steal Cmd/Ctrl+K (global search) */

  useEffect(() => {

    const onKey = (e: KeyboardEvent) => {

      if (!(e.metaKey || e.ctrlKey) || !e.shiftKey) return

      if (e.key.toLowerCase() !== 'a') return

      const target = e.target as HTMLElement | null

      if (target?.closest('input, textarea, [contenteditable="true"]')) return

      e.preventDefault()

      onOpenChange(!open)

    }

    window.addEventListener('keydown', onKey)

    return () => window.removeEventListener('keydown', onKey)

  }, [open, onOpenChange])



  useEffect(() => {

    if (!open) return

    for (const item of sections.built.comingSoon) {

      try {

        trackProductEvent('app_launcher.coming_soon_viewed', {

          currentProductId,

          selectedProductId: item.space.engineProductId ?? item.space.id,

          source: previewMode ? 'sandbox' : 'workspace',

        })

      } catch {

        /* ignore */

      }

    }

  }, [open, sections.built.comingSoon, currentProductId, previewMode])



  const panel = (embedded: boolean) => (

    <AppLauncherPanel

      sections={sections.built}

      resolveContext={context}

      onSelect={handleSelect}

      onUnavailableClick={handleUnavailable}

      errorMessage={errorMessage}

      panelId={panelId}

      embedded={embedded}

      onNavigateAway={() => onOpenChange(false)}

      searchInputRef={searchInputRef}

    />

  )



  return (

    <>

      <AppLauncherTrigger

        ref={triggerRef}

        open={open}

        onClick={() => onOpenChange(!open)}

        controlsId={panelId}

        className={className}

        compact={compactTrigger || isMobile}

      />

      {isMobile ? (

        <Drawer

          open={open}

          onOpenChange={onOpenChange}

          side="bottom"

          size="lg"

          title={TITLE}

          description={DESCRIPTION}

          closeOnEscape

          closeOnBackdrop

          initialFocusRef={searchInputRef}

          returnFocusRef={triggerRef}

        >

          {panel(true)}

        </Drawer>

      ) : (

        <Dialog

          open={open}

          onOpenChange={onOpenChange}

          title={TITLE}

          description={DESCRIPTION}

          size="xl"

          className="app-launcher-dialog"

          closeOnEscape

          closeOnBackdrop

          aria-label="Hub espaces ELFIS"

          initialFocusRef={searchInputRef}

          returnFocusRef={triggerRef}

        >

          {panel(false)}

        </Dialog>

      )}

    </>

  )

}


