/**
 * Mappe les signaux Home réels → Insight Framework (présentation seule).
 * N’invente ni confiance ni contenu métier.
 */

import type { Insight } from '../insight-framework'
import { createInsightAction, sortInsightsByPriority } from '../insight-framework'
import type { HomeSignal } from './homeSignals'

export function mapHomeSignalsToInsights(signals: HomeSignal[]): Insight[] {
  const insights: Insight[] = signals.map((s) => {
    const attention = s.tone === 'attention'
    return {
      id: `home-signal-${s.id}`,
      type: attention ? 'attention' : s.tone === 'calm' ? 'success' : 'suggestion',
      severity: attention ? 'high' : 'medium',
      title: s.label,
      summary: attention
        ? 'Signal plateforme observé — action recommandée.'
        : 'Contexte plateforme — informative.',
      source: { id: 'home-cockpit', label: 'ELFIS Home' },
      context: { surface: 'home', meta: { signalId: s.id } },
      actions: s.href
        ? [
            createInsightAction('open', {
              id: `open-${s.id}`,
              label: 'Ouvrir',
              href: s.href,
              primary: attention,
            }),
          ]
        : undefined,
    } satisfies Insight
  })

  if (insights.length === 0) {
    return [
      {
        id: 'home-signal-calm',
        type: 'confirmation',
        severity: 'info',
        title: 'Plateforme calme',
        summary: 'Aucun signal prioritaire — reprenez là où vous étiez.',
        source: { id: 'home-cockpit', label: 'ELFIS Home' },
        context: { surface: 'home' },
        actions: [
          createInsightAction('open', {
            id: 'resume',
            label: 'Continuer mon travail',
            href: '#home-continue',
            primary: true,
          }),
        ],
      },
    ]
  }

  return sortInsightsByPriority(insights)
}
