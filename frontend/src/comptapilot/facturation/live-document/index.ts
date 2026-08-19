/**
 * Live Document Experience V1 — helpers présentation Composer.
 * Pas de nouveau Framework / moteur : assemblage des briques existantes.
 */

export {
  deriveLiveDocumentStatus,
  type DeriveLiveDocumentStatusInput,
  type LiveDocumentStatusView,
} from './status'

export {
  deriveLiveDocumentInsights,
  STANDARD_FR_VAT_RATES,
  RECENT_PRODUCT_DAYS,
  type DeriveLiveDocumentInsightsInput,
} from './insights'

export {
  snapshotLiveTotals,
  draftDiscountTotal,
  lineDiscountAmount,
  formatDueDateLabel,
  type LiveTotalsSnapshot,
} from './totals'

export { LiveTotals } from './LiveTotals'
export { LiveInsightsPanel } from './LiveInsightsPanel'
