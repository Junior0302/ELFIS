/**
 * Tokens plateforme unifiés — consolidation Theme Engine / foundation (pas un 2e DS).
 * Valeurs = aliases vers --space-* / --radius-* / --shadow-* / typo / surfaces déjà en :root.
 */

import {
  CONTAINER_SCALE,
  FOUNDATION_CSS_VARS,
  RADIUS_SCALE,
  SHADOW_SCALE,
  SPACE_SCALE,
} from '../design-system/tokens/foundationTokens'

/** Spacing scale partagée (4–48). */
export const PLATFORM_SPACE = SPACE_SCALE

/** Radius partagés. */
export const PLATFORM_RADIUS = RADIUS_SCALE

/** Ombres partagées — teinte neutre plateforme (même échelle rem / px). */
export const PLATFORM_SHADOW = SHADOW_SCALE

/** Largeurs container page. */
export const PLATFORM_CONTAINER = CONTAINER_SCALE

/** Surfaces chrome / page (indépendantes de l’accent Pilot). */
export const PLATFORM_SURFACES = {
  page: '#F5F7FA',
  card: '#FFFFFF',
  topbar: '#071629',
  topbarSurface: '#102746',
  /** Navy unique — Core / Compta / Sales (accent Pilot seulement sur actif). */
  sidebar: '#071629',
  muted: '#F8FAFC',
} as const

/** Borders chrome / contenu. */
export const PLATFORM_BORDERS = {
  subtle: 'rgba(7, 22, 41, 0.08)',
  topbar: 'rgba(255, 255, 255, 0.08)',
  strong: 'rgba(7, 22, 41, 0.16)',
} as const

/** Typographie plateforme (fonts déjà déclarées :root). */
export const PLATFORM_TYPOGRAPHY = {
  fontDisplay: 'var(--font-display)',
  fontBody: 'var(--font-body)',
  sizeXs: '0.72rem',
  sizeSm: '0.875rem',
  sizeMd: '1rem',
  sizeLg: '1.125rem',
  sizeXl: '1.5rem',
  weightRegular: '400',
  weightMedium: '500',
  weightSemibold: '600',
  weightBold: '700',
  lineTight: '1.25',
  lineNormal: '1.5',
} as const

/** Largeur page frame pilote (1680px) — source de vérité ElfisPageFrame. */
export const PLATFORM_PAGE_FRAME_MAX_WIDTH = '1680px'

/** Paddings frame — desktop 32 / laptop 24 / tablet 20 / mobile 16. */
export const PLATFORM_PAGE_FRAME_PAD = {
  inlineDesktop: SPACE_SCALE[8], // 32
  inlineLaptop: SPACE_SCALE[6], // 24
  inlineTablet: SPACE_SCALE[5], // 20
  inlineMobile: SPACE_SCALE[4], // 16
  blockMin: SPACE_SCALE[6], // 24
  blockMax: SPACE_SCALE[10], // 40
} as const

/** Hauteurs cards dashboard. */
export const PLATFORM_CARD_DIMS = {
  metricMinHeight: '132px',
  chartBodyMin: '300px',
  chartBodyMax: '420px',
  chartHeroMin: '340px',
  chartHeroMax: '480px',
} as const

/** Gaps grille dashboard — desktop 24 / laptop 20 / mobile 16. */
export const PLATFORM_DASHBOARD_GAPS = {
  desktop: SPACE_SCALE[6],
  laptop: SPACE_SCALE[5],
  mobile: SPACE_SCALE[4],
} as const

/** Dimensions shell — UI.P1 (ne pas diverger par Pilot). */
export const PLATFORM_SHELL_DIMENSIONS = {
  topbarHeight: '64px',
  sidebarExpanded: '240px',
  sidebarCollapsed: '56px',
  sidebarTransitionMs: 180,
  /** 1680px — ElfisPageFrame (pas container-xl 1200). */
  pageMaxWidth: PLATFORM_PAGE_FRAME_MAX_WIDTH,
  pagePaddingInline: PLATFORM_PAGE_FRAME_PAD.inlineDesktop,
  pagePaddingBlock: PLATFORM_PAGE_FRAME_PAD.blockMin,
} as const

/** CSS custom properties exposées sous .up-shell / data-unified-ui. */
export const PLATFORM_TOKEN_CSS_VARS = {
  ...FOUNDATION_CSS_VARS,
  surface: {
    page: '--up-surface-page',
    card: '--up-surface-card',
    topbar: '--up-surface-topbar',
    topbarSurface: '--up-surface-topbar-elevated',
    sidebar: '--up-surface-sidebar',
    muted: '--up-surface-muted',
  },
  border: {
    subtle: '--up-border-subtle',
    topbar: '--up-border-topbar',
    strong: '--up-border-strong',
  },
  typography: {
    fontDisplay: '--up-font-display',
    fontBody: '--up-font-body',
    sizeSm: '--up-font-size-sm',
    sizeMd: '--up-font-size-md',
    sizeLg: '--up-font-size-lg',
  },
  shell: {
    topbarHeight: '--up-topbar-h',
    sidebarExpanded: '--up-sidebar-expanded',
    sidebarCollapsed: '--up-sidebar-collapsed',
    pageMaxWidth: '--up-page-max-width',
    pagePadInline: '--up-page-pad-inline',
    pagePadBlock: '--up-page-pad-block',
  },
} as const

export type PlatformSpaceToken = keyof typeof PLATFORM_SPACE
export type PlatformRadiusToken = keyof typeof PLATFORM_RADIUS
