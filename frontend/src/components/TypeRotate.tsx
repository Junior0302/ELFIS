import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'

const WORDS = [
  'la comptabilité',
  'la facturation',
  'la trésorerie',
  'les décisions',
  'le pilotage',
  "l'OCR intelligent",
]

export default function TypeRotate({ className }: { className?: string }) {
  const [text, setText] = useState('')
  const wordRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setText(WORDS[0])
      return
    }

    let cancelled = false
    let timeout: number | undefined
    let wordIndex = 0

    const run = async () => {
      while (!cancelled) {
        const word = WORDS[wordIndex]
        setText('')

        for (let i = 0; i <= word.length; i++) {
          if (cancelled) return
          setText(word.slice(0, i))
          await new Promise((r) => {
            timeout = window.setTimeout(r, 42 + Math.random() * 28)
          })
        }

        if (wordRef.current) {
          gsap.fromTo(
            wordRef.current,
            { y: 4, opacity: 0.7 },
            { y: 0, opacity: 1, duration: 0.25, ease: 'power2.out' },
          )
        }

        await new Promise((r) => {
          timeout = window.setTimeout(r, 1600)
        })
        if (cancelled) return

        for (let i = word.length; i >= 0; i--) {
          if (cancelled) return
          setText(word.slice(0, i))
          await new Promise((r) => {
            timeout = window.setTimeout(r, 22)
          })
        }

        wordIndex = (wordIndex + 1) % WORDS.length
      }
    }

    run()
    return () => {
      cancelled = true
      if (timeout) window.clearTimeout(timeout)
    }
  }, [])

  return (
    <span className={className} aria-live="polite">
      <span className="home-type-word" ref={wordRef}>
        {text}
      </span>
      <span className="home-type-caret" aria-hidden="true" />
      <span className="sr-only">Facilite {WORDS.join(', ')}</span>
    </span>
  )
}
