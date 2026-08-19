/**

 * Unified Platform UI — Vague 1 (shell) + Vague 2 (primitives).

 */



export {

  isUnifiedPlatformUiEnabled,

  setUnifiedPlatformUiEnabled,

  resetUnifiedPlatformUiFlag,

  UNIFIED_PLATFORM_UI_STORAGE_KEY,

  UNIFIED_PLATFORM_UI_ENV_KEY,

} from './featureFlag'



export {

  PLATFORM_SPACE,

  PLATFORM_RADIUS,

  PLATFORM_SHADOW,

  PLATFORM_CONTAINER,

  PLATFORM_SURFACES,

  PLATFORM_BORDERS,

  PLATFORM_TYPOGRAPHY,

  PLATFORM_SHELL_DIMENSIONS,

  PLATFORM_PAGE_FRAME_MAX_WIDTH,

  PLATFORM_PAGE_FRAME_PAD,

  PLATFORM_CARD_DIMS,

  PLATFORM_DASHBOARD_GAPS,

  PLATFORM_TOKEN_CSS_VARS,

} from './platformTokens'



export {

  resolvePilotTheme,

  isUnifiedPilotId,

  PILOT_ACCENT_EXPECTATIONS,

  type UnifiedPilotId,

  type PilotAccentContract,

} from './PilotTheme'



export {

  PilotThemeProvider,

  usePilotTheme,

  usePilotThemeId,

  type PilotThemeProviderProps,

  type PilotThemeContextValue,

} from './PilotThemeProvider'



export {

  ElfisUnifiedShell,

  GlobalTopbar,

  PilotSidebar,

  PilotContentLayout,

  PilotWorkspace,

  type ElfisUnifiedShellProps,

  type PilotWorkspaceProps,

  type PlatformShellSidebarApi,

} from './ElfisUnifiedShell'



export {

  PlatformPageContainer,

  type PlatformPageContainerProps,

} from './PlatformPageContainer'



export {

  PlatformGrid,

  GridItem,

  type PlatformGridProps,

  type PlatformGridColumns,

  type GridItemProps,

  type GridItemSpan,

} from './PlatformGrid'



export {

  NavigationSystem,

  DomainNav,

  GlobalNavLinks,

  ContextualSubNav,

  ElfisNavSection,

  ElfisNavItem,

  type ElfisDomainNavConfig,

  type ElfisGlobalNavLink,

  type ElfisNavigationItem,

  type ElfisNavigationSection,

} from './navigation/NavigationSystem'



export {

  ElfisIcon,

  resolveElfisIcon,

  PLATFORM_ICON_GLYPHS,

  ELFIS_NAV_ICON_BY_PATH,

  type ElfisIconId,

} from './icons/ElfisIconSystem'



export { PageLayout, type PageLayoutProps } from './primitives/PageLayout'

export {
  ElfisPageFrame,
  type ElfisPageFrameProps,
  type ElfisPageFramePadding,
} from './primitives/ElfisPageFrame'

export {
  WorkspacePageFrame,
  type WorkspacePageFrameProps,
} from './WorkspacePageFrame'

export { ElfisPageHeader, type ElfisPageHeaderProps } from './primitives/ElfisPageHeader'

export {

  ElfisDashboardTemplate,

  ElfisDashboardGrid,

  ElfisDashboardGridItem,

  sanitizeDashboardClassName,

  type ElfisDashboardTemplateProps,

} from './primitives/ElfisDashboardTemplate'

export { ChartCard, type ChartCardProps, type ChartCardVariant } from './primitives/ChartCard'

export {
  ResponsiveChartFrame,
  type ResponsiveChartFrameProps,
} from './primitives/ResponsiveChartFrame'

export { DisplayTitle, BodyText, Eyebrow } from './primitives/Typography'



export {

  ElfisMetricCard,

  ElfisStatCard,

  ElfisSurfaceCard,

  ElfisButton,

  ElfisButtonLink,

  ElfisFormField,

  ElfisField,

  ElfisInput,

  ElfisTable,

  ElfisDialog,

  ElfisDialogContent,

  ElfisDialogDescription,

  ElfisDialogFooter,

  ElfisDialogHeader,

  ElfisDialogTitle,

  ElfisConfirmDialog,

  ElfisEmptyState,

  ElfisLoadingState,

  ElfisErrorState,

  MotionSystem,

  MotionPage,

  type ElfisButtonLinkProps,

} from './primitives/DsWrappers'


