/**
 * Panneau Insights live — apparition progressive, Insight Framework réel.
 */

import { useEffect, useMemo, useState } from 'react'
import { InsightList, type Insight } from '../../../insight-framework'
import './live-document.css'

export function LiveInsightsPanel({
  insights,
  emptyMessage = 'Aucun insight pour l’instant.',
  staggerMs = 80,
}: {
  insights: Insight[]
  emptyMessage?: string
  staggerMs?: number
}) {
  const [visibleCount, setVisibleCount] = useState(0)
  const idsKey = useMemo(() => insights.map((i) => i.id).join('|'), [insights])

  useEffect(() => {
    setVisibleCount(0)
    if (!insights.length) return
    let n = 0
    const tick = () => {
      n += 1
      setVisibleCount(n)
      if (n < insights.length) {
        timer = window.setTimeout(tick, staggerMs)
      }
    }
    let timer = window.setTimeout(tick, 40)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset on insight id set
  }, [idsKey, staggerMs])

  const shown = insights.slice(0, visibleCount)

  return (
    <div className="ld-insights" aria-live="polite" aria-relevant="additions" aria-label="Insights document">
      <p className="ld-insights__title">Points d’attention</p>
      <InsightList insights={shown} emptyMessage={emptyMessage} variant="inline" />
    </div>
  )
}
