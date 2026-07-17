import { useEffect, useRef } from 'react'

type Particle = {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  a: number
  hue: 'forest' | 'mint' | 'amber'
  pulse: number
  pulseSpeed: number
}

type Spark = {
  x: number
  y: number
  life: number
  max: number
  r: number
  vx: number
  vy: number
}

const COLORS = {
  forest: [11, 61, 46] as const,
  mint: [123, 196, 160] as const,
  amber: [196, 120, 43] as const,
}

export default function HomeParticles() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let particles: Particle[] = []
    let sparks: Spark[] = []
    let raf = 0
    let width = 0
    let height = 0
    let mouseX = -9999
    let mouseY = -9999
    let prevMouseX = -9999
    let prevMouseY = -9999
    let t = 0
    let paused = document.visibilityState === 'hidden'

    const count = () => {
      const coarse = window.matchMedia('(pointer: coarse)').matches
      const base = Math.floor((width * height) / (coarse ? 16000 : 10000))
      return coarse ? Math.max(36, Math.min(70, base)) : Math.max(70, Math.min(130, base))
    }

    const spawn = (): Particle => {
      const roll = Math.random()
      const hue: Particle['hue'] = roll > 0.82 ? 'amber' : roll > 0.45 ? 'mint' : 'forest'
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.42,
        vy: (Math.random() - 0.5) * 0.42,
        r: 0.8 + Math.random() * 2.4,
        a: 0.16 + Math.random() * 0.42,
        hue,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.012 + Math.random() * 0.02,
      }
    }

    const resize = () => {
      width = window.innerWidth
      height = window.innerHeight
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      particles = Array.from({ length: count() }, spawn)
    }

    const onMove = (e: PointerEvent) => {
      prevMouseX = mouseX
      prevMouseY = mouseY
      mouseX = e.clientX
      mouseY = e.clientY

      if (reduceMotion || paused) return
      const speed = Math.hypot(mouseX - prevMouseX, mouseY - prevMouseY)
      if (speed > 3 && sparks.length < 48) {
        for (let i = 0; i < 2; i++) {
          sparks.push({
            x: mouseX + (Math.random() - 0.5) * 10,
            y: mouseY + (Math.random() - 0.5) * 10,
            life: 1,
            max: 0.55 + Math.random() * 0.45,
            r: 1 + Math.random() * 2.2,
            vx: (Math.random() - 0.5) * 1.4,
            vy: (Math.random() - 0.5) * 1.4 - 0.4,
          })
        }
      }
    }

    const draw = () => {
      if (paused) {
        raf = requestAnimationFrame(draw)
        return
      }
      t += 1
      ctx.clearRect(0, 0, width, height)

      if (!reduceMotion) {
        const g1 = ctx.createRadialGradient(
          width * 0.2 + Math.sin(t * 0.004) * 40,
          height * 0.15,
          0,
          width * 0.2,
          height * 0.2,
          width * 0.35,
        )
        g1.addColorStop(0, 'rgba(123, 196, 160, 0.07)')
        g1.addColorStop(1, 'rgba(123, 196, 160, 0)')
        ctx.fillStyle = g1
        ctx.fillRect(0, 0, width, height)

        const g2 = ctx.createRadialGradient(
          width * 0.82 + Math.cos(t * 0.003) * 50,
          height * 0.35,
          0,
          width * 0.85,
          height * 0.4,
          width * 0.3,
        )
        g2.addColorStop(0, 'rgba(196, 120, 43, 0.05)')
        g2.addColorStop(1, 'rgba(196, 120, 43, 0)')
        ctx.fillStyle = g2
        ctx.fillRect(0, 0, width, height)
      }

      if (mouseX > 0 && !reduceMotion) {
        const glow = ctx.createRadialGradient(mouseX, mouseY, 0, mouseX, mouseY, 180)
        glow.addColorStop(0, 'rgba(123, 196, 160, 0.12)')
        glow.addColorStop(0.45, 'rgba(11, 61, 46, 0.04)')
        glow.addColorStop(1, 'rgba(11, 61, 46, 0)')
        ctx.fillStyle = glow
        ctx.fillRect(mouseX - 180, mouseY - 180, 360, 360)
      }

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        p.pulse += p.pulseSpeed

        if (!reduceMotion) {
          p.x += p.vx + Math.sin(t * 0.01 + p.pulse) * 0.08
          p.y += p.vy + Math.cos(t * 0.008 + p.pulse) * 0.08

          if (p.x < -30) p.x = width + 30
          if (p.x > width + 30) p.x = -30
          if (p.y < -30) p.y = height + 30
          if (p.y > height + 30) p.y = -30

          const dx = mouseX - p.x
          const dy = mouseY - p.y
          const dist = Math.hypot(dx, dy)
          if (dist < 180 && dist > 0.1) {
            const force = (180 - dist) / 180
            p.vx -= (dx / dist) * force * 0.022
            p.vy -= (dy / dist) * force * 0.022
          }
          p.vx *= 0.992
          p.vy *= 0.992
          const speed = Math.hypot(p.vx, p.vy)
          if (speed > 1.6) {
            p.vx *= 1.6 / speed
            p.vy *= 1.6 / speed
          }
        }

        const [cr, cg, cb] = COLORS[p.hue]
        const alpha = p.a * (0.75 + Math.sin(p.pulse) * 0.25)
        const radius = p.r * (0.85 + Math.sin(p.pulse * 1.3) * 0.2)

        const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius * 4)
        halo.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, ${alpha * 0.35})`)
        halo.addColorStop(1, `rgba(${cr}, ${cg}, ${cb}, 0)`)
        ctx.fillStyle = halo
        ctx.beginPath()
        ctx.arc(p.x, p.y, radius * 4, 0, Math.PI * 2)
        ctx.fill()

        ctx.beginPath()
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${cr}, ${cg}, ${cb}, ${alpha})`
        ctx.fill()

        for (let j = i + 1; j < particles.length; j++) {
          const q = particles[j]
          const d = Math.hypot(p.x - q.x, p.y - q.y)
          if (d < 128) {
            const strength = 1 - d / 128
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(q.x, q.y)
            ctx.strokeStyle = `rgba(11, 61, 46, ${0.12 * strength})`
            ctx.lineWidth = 1
            ctx.stroke()
          }
        }

        if (mouseX > 0) {
          const md = Math.hypot(p.x - mouseX, p.y - mouseY)
          if (md < 160) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(mouseX, mouseY)
            ctx.strokeStyle = `rgba(123, 196, 160, ${0.14 * (1 - md / 160)})`
            ctx.lineWidth = 1
            ctx.stroke()
          }
        }
      }

      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i]
        s.life -= 0.025
        s.x += s.vx
        s.y += s.vy
        s.vy += 0.02
        if (s.life <= 0) {
          sparks.splice(i, 1)
          continue
        }
        const a = (s.life / s.max) * 0.7
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r * s.life, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(123, 196, 160, ${a})`
        ctx.fill()
      }

      raf = requestAnimationFrame(draw)
    }

    const onVis = () => {
      paused = document.visibilityState === 'hidden'
    }

    resize()
    draw()
    window.addEventListener('resize', resize)
    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('visibilitychange', onVis)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  return <canvas className="home-particles" ref={canvasRef} aria-hidden="true" />
}
