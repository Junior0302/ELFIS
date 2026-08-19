/**
 * ResponsiveChartFrame — ResizeObserver pour charts SVG (largeur parent réelle).
 */

import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cx } from '../../design-system'

export type ResponsiveChartFrameProps = {
  children: (width: number) => ReactNode
  className?: string
  /** Largeur mini avant render (évite flash 0). */
  minWidth?: number
}

export function ResponsiveChartFrame({
  children,
  className,
  minWidth = 120,
}: ResponsiveChartFrameProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') {
      if (el) setWidth(Math.floor(el.getBoundingClientRect().width))
      return
    }
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      setWidth(Math.floor(entry.contentRect.width))
    })
    ro.observe(el)
    setWidth(Math.floor(el.getBoundingClientRect().width))
    return () => ro.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={cx('up-chart-responsive', className)}
      data-chart-responsive="v1"
      data-chart-width={width > 0 ? String(width) : undefined}
    >
      {width >= minWidth ? children(width) : (
        <div className="up-chart-responsive__placeholder" aria-hidden />
      )}
    </div>
  )
}
