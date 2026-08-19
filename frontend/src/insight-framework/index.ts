/**
 * ELFIS Insight Framework V1 — API publique.
 * Présentation d’informations intelligentes (pas de calcul métier).
 */

import './insight-framework.css'

export type {
  Insight,
  InsightAction,
  InsightActionKind,
  InsightConfidence,
  InsightContext,
  InsightIconName,
  InsightLinkedResource,
  InsightRenderProps,
  InsightSeverity,
  InsightSource,
  InsightToneTokens,
  InsightType,
} from './types'

export {
  createInsightAction,
  insightActionLabel,
  INSIGHT_ACTION_KINDS,
} from './actions'

export {
  compareInsightPriority,
  insightTypeLabelFr,
  resolveInsightTone,
  severityLabelFr,
  severityRank,
  sortInsightsByPriority,
  SEVERITY_LABEL_FR,
  SEVERITY_RANK,
  TYPE_DEFAULTS,
} from './tokens'

export {
  mapComposerIssueToInsight,
  mapComposerIssuesToInsights,
  mapDayPrioritiesToInsights,
  mapDayPriorityToInsight,
  mapFinancialAlertToInsight,
  mapFinancialAlertsToInsights,
  mapHealthToInsights,
} from './mappers'

export {
  InsightActions,
  InsightBadge,
  InsightBanner,
  InsightCard,
  InsightFooter,
  InsightHeader,
  InsightIcon,
  InsightInline,
  InsightList,
  InsightStack,
  InsightToast,
} from './InsightComponents'
