export { OverlayProvider, useOverlayContext, useOverlayContextOptional } from './OverlayProvider'
export type { OverlayEntry, OverlayKind } from './OverlayProvider'
export { OverlayRouteBridge } from './OverlayRouteBridge'
export {
  useOverlayManager,
  useOverlayManagerOptional,
  useOverlayStackDebug,
} from './hooks/useOverlayManager'
export type { OverlayManagerApi } from './OverlayContext'
export { Portal, type PortalProps } from './Portal'
export {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogFooter,
  DialogClose,
  type DialogProps,
  type DialogSize,
} from './Dialog'
export { ConfirmDialog, type ConfirmDialogProps, type ConfirmTone } from './ConfirmDialog'
export { Drawer, type DrawerProps, type DrawerSide, type DrawerSize } from './Drawer'
export { Tooltip, type TooltipProps, type TooltipPlacement } from './Tooltip'
export { Popover, type PopoverProps, type PopoverPlacement } from './Popover'
export { OVERLAY_Z, OVERLAY_Z_CSS_VARS, OVERLAY_ROOT_ID } from './utils/zIndex'
export { getFocusableElements, focusFirstElement, restoreFocus } from './utils/focus'
export { lockBodyScroll, __resetScrollLockForTests } from './utils/scrollLock'
export {
  createOverlayManager,
  closeAllOverlays,
  bindOverlayCloseAll,
  OVERLAY_LIFECYCLE_HOOKS,
  OVERLAY_EVENT,
  resolvePriority,
  computeOverlayZIndex,
  sortStack,
  assertSafeEventDetail,
  type OverlayManager,
  type OverlayType,
  type OverlayPriority,
  type OverlayCloseReason,
  type OverlayDescriptor,
  type RegisterOverlayInput,
  type OverlayStackSnapshot,
  type OverlayEventDetail,
} from './manager'
