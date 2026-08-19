/**
 * Totaux vivants — recalcul immédiat via draftAmount* ; animation discrète.
 */

import { useEffect, useRef, useState } from 'react'
import { formatEuro } from '../../../api'
import type { LiveTotalsSnapshot } from './totals'
import './live-document.css'

export function LiveTotals({
  totals,
  vatRate,
}: {
  totals: LiveTotalsSnapshot
  vatRate: number
}) {
  const [flash, setFlash] = useState(false)
  const prev = useRef(totals.ttc)

  useEffect(() => {
    if (prev.current === totals.ttc) return
    prev.current = totals.ttc
    setFlash(true)
    const id = window.setTimeout(() => setFlash(false), 420)
    return () => window.clearTimeout(id)
  }, [totals.ttc])

  return (
    <div
      className={`ld-totals${flash ? ' is-flash' : ''}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-label="Totaux du document"
    >
      <dl className="ld-totals__dl fp-composer-inspector-dl">
        <div>
          <dt>Sous-total HT</dt>
          <dd>{formatEuro(totals.ht)}</dd>
        </div>
        {totals.discountTotal > 0 ? (
          <div>
            <dt>Remises</dt>
            <dd>−{formatEuro(totals.discountTotal)}</dd>
          </div>
        ) : null}
        <div>
          <dt>TVA ({vatRate} %)</dt>
          <dd>{formatEuro(totals.tva)}</dd>
        </div>
        <div className="ld-totals__ttc">
          <dt>Total TTC</dt>
          <dd>
            <strong>{formatEuro(totals.ttc)}</strong>
          </dd>
        </div>
        <div>
          <dt>Échéance</dt>
          <dd>
            {totals.dueDays} j. · {totals.dueDateLabel}
          </dd>
        </div>
      </dl>
    </div>
  )
}
