import { useEffect, useRef } from 'react'

export default function HomeCursor() {
  const dotRef = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)').matches
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!fine || reduce) return

    const page = document.querySelector('.home-page') as HTMLElement | null
    const dot = dotRef.current
    const ring = ringRef.current
    if (!page || !dot || !ring) return

    page.classList.add('home-cursor-scope')
    let x = window.innerWidth / 2
    let y = window.innerHeight / 2
    let rx = x
    let ry = y
    let raf = 0
    let visible = false

    const show = () => {
      if (visible) return
      visible = true
      dot.classList.add('is-on')
      ring.classList.add('is-on')
    }

    const onMove = (e: PointerEvent) => {
      x = e.clientX
      y = e.clientY
      show()
      dot.style.transform = `translate3d(${x}px, ${y}px, 0)`
    }

    const onOver = (e: PointerEvent) => {
      const t = e.target as HTMLElement | null
      const hovering = Boolean(
        t?.closest('a, button, .btn, .home-benefit-card, .home-pricing-card, input, label'),
      )
      ring.classList.toggle('is-hover', hovering)
      dot.classList.toggle('is-hover', hovering)
    }

    const onOut = (e: PointerEvent) => {
      const related = e.relatedTarget as Node | null
      if (related && page.contains(related)) return
      ring.classList.remove('is-hover')
      dot.classList.remove('is-hover')
    }

    const tick = () => {
      rx += (x - rx) * 0.18
      ry += (y - ry) * 0.18
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0)`
      raf = requestAnimationFrame(tick)
    }

    page.addEventListener('pointermove', onMove, { passive: true })
    page.addEventListener('pointerover', onOver, { passive: true })
    page.addEventListener('pointerout', onOut, { passive: true })
    raf = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(raf)
      page.classList.remove('home-cursor-scope')
      page.removeEventListener('pointermove', onMove)
      page.removeEventListener('pointerover', onOver)
      page.removeEventListener('pointerout', onOut)
      document.documentElement.classList.remove('home-cursor-active')
    }
  }, [])

  return (
    <>
      <div className="home-cursor-dot" ref={dotRef} aria-hidden="true" />
      <div className="home-cursor-ring" ref={ringRef} aria-hidden="true" />
    </>
  )
}
