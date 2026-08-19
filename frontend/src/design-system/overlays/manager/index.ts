export type {
  OverlayType,
  OverlayPriority,
  OverlayStatus,
  OverlayCloseReason,
  OverlayDescriptor,
  RegisterOverlayInput,
  OverlayStackSnapshot,
  OverlayEventDetail,
} from './types'
export { OVERLAY_EVENT } from './types'
export {
  resolvePriority,
  comparePriority,
  computeOverlayZIndex,
  defaultCloseOnRouteChange,
  priorityRank,
} from './overlayPriority'
export {
  sortStack,
  upsertDescriptor,
  removeDescriptor,
  getTop,
  isTop,
  collectDescendantIds,
  closeOrderForParent,
  closeAllOrder,
} from './overlayStack'
export { createOverlayManager, type OverlayManager, type CreateOverlayManagerOptions } from './overlayManager'
export { bindOverlayCloseAll, closeAllOverlays, OVERLAY_LIFECYCLE_HOOKS } from './overlayLifecycle'
export { emitOverlayOpened, emitOverlayClosed, assertSafeEventDetail } from './overlayEvents'
