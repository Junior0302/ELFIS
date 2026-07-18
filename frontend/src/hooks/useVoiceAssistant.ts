import { useCallback, useEffect, useRef, useState } from 'react'
import { cancelSpeech, speakFrench, speechSupported, warmSpeechVoices } from '../voice/speech'

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

export function useVoiceAssistant(options?: {
  lang?: string
  onFinalTranscript?: (text: string) => void
}) {
  const lang = options?.lang || 'fr-FR'
  const onFinalRef = useRef(options?.onFinalTranscript)
  onFinalRef.current = options?.onFinalTranscript

  const [supported] = useState(() => Boolean(getSpeechRecognitionCtor() && speechSupported()))
  const [phase, setPhase] = useState<VoicePhase>(() =>
    getSpeechRecognitionCtor() && speechSupported() ? 'idle' : 'unsupported',
  )
  const [interim, setInterim] = useState('')
  const [error, setError] = useState('')
  const [autoSpeak, setAutoSpeak] = useState(true)

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const sessionRef = useRef(0)
  const wantListenRef = useRef(false)
  const phaseRef = useRef<VoicePhase>(phase)
  phaseRef.current = phase

  const stopSpeaking = useCallback(() => {
    cancelSpeech()
    if (phaseRef.current === 'speaking') setPhase('idle')
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!supported || !text.trim()) return
      speakFrench(text, {
        lang,
        onStart: () => setPhase('speaking'),
        onEnd: () => {
          if (phaseRef.current === 'speaking') setPhase('idle')
        },
      })
    },
    [lang, supported],
  )

  const stopListening = useCallback(() => {
    wantListenRef.current = false
    sessionRef.current += 1
    const rec = recognitionRef.current
    recognitionRef.current = null
    if (rec) {
      try {
        rec.onresult = null
        rec.onerror = null
        rec.onend = null
        rec.onstart = null
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

    // Contexte non sécurisé (sauf localhost)
    if (
      typeof window !== 'undefined' &&
      !window.isSecureContext &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
    ) {
      setError('Le micro nécessite une connexion HTTPS.')
      return
    }

    stopSpeaking()
    setError('')
    setInterim('')

    const prev = recognitionRef.current
    recognitionRef.current = null
    if (prev) {
      try {
        prev.onresult = null
        prev.onerror = null
        prev.onend = null
        prev.onstart = null
        prev.abort()
      } catch {
        /* ignore */
      }
    }

    const session = sessionRef.current + 1
    sessionRef.current = session
    wantListenRef.current = true

    const rec = new Ctor()
    recognitionRef.current = rec
    rec.lang = lang
    rec.continuous = false
    rec.interimResults = true
    rec.maxAlternatives = 1

    const isCurrent = () => recognitionRef.current === rec && sessionRef.current === session

    rec.onstart = () => {
      if (isCurrent() && wantListenRef.current) setPhase('listening')
    }
    rec.onresult = (event) => {
      if (!isCurrent()) return
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
      if (!isCurrent()) return
      const code = event.error || ''
      // « aborted » = remplacement volontaire d’une session — ne pas casser wantListen
      if (code === 'aborted') return
      wantListenRef.current = false
      setInterim('')
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        setError('Micro refusé. Autorisez le microphone dans le navigateur.')
      } else if (code === 'no-speech') {
        setError('Aucune parole détectée. Réessayez.')
      } else if (code === 'network') {
        setError('Réseau vocal indisponible. Réessayez.')
      } else {
        setError('Écoute interrompue. Réessayez.')
      }
      setPhase('idle')
    }
    rec.onend = () => {
      if (!isCurrent()) return
      if (wantListenRef.current) {
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
      recognitionRef.current = null
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
    if (!supported) return
    warmSpeechVoices()
    return () => {
      wantListenRef.current = false
      sessionRef.current += 1
      try {
        recognitionRef.current?.abort()
      } catch {
        /* ignore */
      }
      recognitionRef.current = null
      cancelSpeech()
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
