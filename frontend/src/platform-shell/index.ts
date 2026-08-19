export { PlatformShell, type PlatformShellProps } from './PlatformShell'
export {
  PlatformTopBar,
  PlatformSidebar,
  WorkspaceViewport,
} from './PlatformTopBar'
export { PlatformBrandLockup } from './PlatformBrandLockup'
export { PlatformLauncher } from './PlatformLauncher'
export { PlatformSearch } from './PlatformSearch'
export { NotificationCenter } from './NotificationCenter'
export { OrganizationSwitcher } from './OrganizationSwitcher'
export { WorkspaceSwitcher } from './WorkspaceSwitcher'
export { UserMenu } from './UserMenu'
export { ProductIndicator } from './ProductIndicator'
export {
  ProductSidebar,
  ProductSidebarHeader,
  ProductSidebarFooter,
  ProductNavigationItem,
  ProductNavigationSection,
} from './ProductNavigation'
export { SalesProductNav } from './SalesProductNav'
export { ComptaProductNav } from './ComptaProductNav'
export {
  getProductShellConfiguration,
  withChromeOverrides,
  type ProductShellConfiguration,
  type ProductShellChromeOptions,
} from './productShellConfig'
export { isPlatformShellPath } from './platformPaths'
export {
  PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY,
  PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX,
  PRODUCT_SIDEBAR_EXPANDED_WIDTH_PX,
  PRODUCT_SIDEBAR_TRANSITION_MS,
  PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT,
  COMPTA_PRODUCT_NAV_ID,
  readProductSidebarCollapsedPreference,
  writeProductSidebarCollapsedPreference,
  notifyProductShellViewportResize,
} from './productSidebarCollapse'
export { useProductSidebarCollapsed } from './useProductSidebarCollapsed'
