import { useCallback, useEffect, useRef, useState } from 'react'

export type VoicePhase = 'idle' | 'listening' | 'processing' | 'speaking' | 'unsupported'

type SpeechRecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: { error?: string }) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

type SpeechRecognitionEventLike = {
  resultIndex: number
  results: ArrayLike<{
    isFinal: boolean
    0: { transcript: string }
  }>
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor
    webkitSpeechRecognition?: SpeechRecognitionCtor
  }
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

function pickFrenchVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null
  const voices = window.speechSynthesis.getVoices()
  const fr = voices.filter((v) => v.lang.toLowerCase().startsWith('fr'))
  return (
    fr.find((v) => /google|natural|enhanced|premium/i.test(v.name)) ||
    fr.find((v) => /france|fr-fr/i.test(v.lang)) ||
    fr[0] ||
    null
  )
}

export function useVoiceAssistant(options?: {
  lang?: string
  onFinalTranscript?: (text: string) => void
}) {
  const lang = options?.lang || 'fr-FR'
  const onFinalRef = useRef(options?.onFinalTranscript)
  onFinalRef.current = options?.onFinalTranscript

  const [supported] = useState(() => Boolean(getSpeechRecognitionCtor() && window.speechSynthesis))
  const [phase, setPhase] = useState<VoicePhase>(() =>
    getSpeechRecognitionCtor() && typeof window !== 'undefined' && window.speechSynthesis
      ? 'idle'
      : 'unsupported',
  )
  const [interim, setInterim] = useState('')
  const [error, setError] = useState('')
  const [autoSpeak, setAutoSpeak] = useState(true)

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const wantListenRef = useRef(false)
  const phaseRef = useRef<VoicePhase>(phase)
  phaseRef.current = phase

  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    if (phaseRef.current === 'speaking') setPhase('idle')
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!supported || !text.trim() || typeof window === 'undefined' || !window.speechSynthesis) {
        return
      }
      window.speechSynthesis.cancel()
      const utter = new SpeechSynthesisUtterance(text.trim())
      utter.lang = lang
      utter.rate = 1.02
      utter.pitch = 0.98
      const voice = pickFrenchVoice()
      if (voice) utter.voice = voice
      utter.onstart = () => setPhase('speaking')
      utter.onend = () => {
        if (phaseRef.current === 'speaking') setPhase('idle')
      }
      utter.onerror = () => {
        if (phaseRef.current === 'speaking') setPhase('idle')
      }
      setPhase('speaking')
      window.speechSynthesis.speak(utter)
    },
    [lang, supported],
  )

  const stopListening = useCallback(() => {
    wantListenRef.current = false
    const rec = recognitionRef.current
    if (rec) {
      try {
        rec.stop()
      } catch {
        try {
          rec.abort()
        } catch {
          /* ignore */
        }
      }
    }
    setInterim('')
    if (phaseRef.current === 'listening') setPhase('idle')
  }, [])

  const startListening = useCallback(() => {
    if (!supported) {
      setPhase('unsupported')
      setError('La dictée vocale n’est pas disponible sur ce navigateur. Utilisez Chrome ou Edge.')
      return
    }
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return

    stopSpeaking()
    setError('')
    setInterim('')
    wantListenRef.current = true

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort()
      } catch {
        /* ignore */
      }
    }

    const rec = new Ctor()
    recognitionRef.current = rec
    rec.lang = lang
    rec.continuous = false
    rec.interimResults = true
    rec.maxAlternatives = 1

    rec.onstart = () => {
      if (wantListenRef.current) setPhase('listening')
    }
    rec.onresult = (event) => {
      let interimText = ''
      let finalText = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript
        if (event.results[i].isFinal) finalText += piece
        else interimText += piece
      }
      if (interimText) setInterim(interimText)
      if (finalText.trim()) {
        setInterim('')
        wantListenRef.current = false
        setPhase('processing')
        onFinalRef.current?.(finalText.trim())
      }
    }
    rec.onerror = (event) => {
      wantListenRef.current = false
      setInterim('')
      const code = event.error || ''
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        setError('Micro refusé. Autorisez le microphone dans le navigateur.')
      } else if (code === 'no-speech') {
        setError('Aucune parole détectée. Réessayez.')
      } else if (code !== 'aborted') {
        setError('Écoute interrompue. Réessayez.')
      }
      setPhase('idle')
    }
    rec.onend = () => {
      if (wantListenRef.current) {
        // Relance courte si le navigateur coupe trop tôt sans résultat final
        try {
          rec.start()
          return
        } catch {
          wantListenRef.current = false
        }
      }
      if (phaseRef.current === 'listening') setPhase('idle')
    }

    try {
      rec.start()
      setPhase('listening')
    } catch {
      setError('Impossible de démarrer le micro.')
      setPhase('idle')
      wantListenRef.current = false
    }
  }, [lang, stopSpeaking, supported])

  const toggleListening = useCallback(() => {
    if (phaseRef.current === 'listening') stopListening()
    else startListening()
  }, [startListening, stopListening])

  const markProcessing = useCallback(() => setPhase('processing'), [])
  const markIdle = useCallback(() => {
    if (phaseRef.current !== 'listening' && phaseRef.current !== 'speaking') {
      setPhase(supported ? 'idle' : 'unsupported')
    }
  }, [supported])

  useEffect(() => {
    if (!supported || typeof window === 'undefined') return
    const warm = () => {
      void pickFrenchVoice()
    }
    warm()
    window.speechSynthesis.addEventListener('voiceschanged', warm)
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', warm)
      wantListenRef.current = false
      try {
        recognitionRef.current?.abort()
      } catch {
        /* ignore */
      }
      window.speechSynthesis.cancel()
    }
  }, [supported])

  return {
    supported,
    phase,
    interim,
    error,
    setError,
    autoSpeak,
    setAutoSpeak,
    startListening,
    stopListening,
    toggleListening,
    speak,
    stopSpeaking,
    markProcessing,
    markIdle,
  }
}
