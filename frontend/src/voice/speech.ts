/** Synthèse vocale FR — récap dashboard (ton chaleureux, lent, humain). */

let speakToken = 0
let voicesReady: Promise<void> | null = null

export function speechSupported(): boolean {
  return typeof window !== 'undefined' && Boolean(window.speechSynthesis)
}

function scoreFrenchVoice(voice: SpeechSynthesisVoice): number {
  const name = voice.name.toLowerCase()
  const lang = voice.lang.toLowerCase()
  let score = 0
  if (lang.startsWith('fr')) score += 5
  if (lang.includes('fr-fr') || lang.includes('fr_fr')) score += 2
  // Voix masculines / neutres plus chaleureuses
  if (/thomas|henri|paul|jacques|nicolas|claude|guy|george|daniel|pierre|male|homme|homme français/.test(name)) {
    score += 12
  }
  if (/natural|neural|enhanced|premium|online \(natural\)/.test(name)) score += 4
  if (/google/.test(name) && /fr/.test(lang)) score += 3
  // Éviter les voix très robotiques / trop aiguës féminines par défaut
  if (/amelie|hortense|julie|marie|audrey|denise|female|femme|zira|susan/.test(name)) score -= 14
  if (/compact|eloquence|espeak|microsoft david/.test(name)) score -= 4
  return score
}

function pickFrenchVoice(): SpeechSynthesisVoice | null {
  if (!speechSupported()) return null
  const voices = window.speechSynthesis.getVoices()
  const fr = voices.filter((v) => v.lang.toLowerCase().startsWith('fr'))
  if (!fr.length) return null
  return [...fr].sort((a, b) => scoreFrenchVoice(b) - scoreFrenchVoice(a))[0] || null
}

function ensureVoices(): Promise<void> {
  if (!speechSupported()) return Promise.resolve()
  if (window.speechSynthesis.getVoices().length > 0) return Promise.resolve()
  if (voicesReady) return voicesReady
  voicesReady = new Promise((resolve) => {
    const done = () => {
      window.speechSynthesis.removeEventListener('voiceschanged', done)
      resolve()
    }
    window.speechSynthesis.addEventListener('voiceschanged', done)
    window.setTimeout(done, 800)
  })
  return voicesReady
}

export function warmSpeechVoices(): void {
  if (!speechSupported()) return
  void ensureVoices().then(() => {
    void pickFrenchVoice()
  })
  window.speechSynthesis.getVoices()
}

export function cancelSpeech(): void {
  speakToken += 1
  if (!speechSupported()) return
  window.speechSynthesis.cancel()
}

export function speakFrench(
  text: string,
  opts?: {
    lang?: string
    rate?: number
    pitch?: number
    onStart?: () => void
    onEnd?: () => void
  },
): void {
  if (!speechSupported() || !text.trim()) {
    opts?.onEnd?.()
    return
  }
  const token = ++speakToken
  window.speechSynthesis.cancel()

  void ensureVoices().then(() => {
    if (token !== speakToken) {
      opts?.onEnd?.()
      return
    }
    const utter = new SpeechSynthesisUtterance(text.trim())
    utter.lang = opts?.lang || 'fr-FR'
    // Plus lent, plus grave → moins robotique
    utter.rate = opts?.rate ?? 0.88
    utter.pitch = opts?.pitch ?? 0.86
    utter.volume = 1
    const voice = pickFrenchVoice()
    if (voice) utter.voice = voice
    utter.onstart = () => {
      if (token === speakToken) opts?.onStart?.()
    }
    utter.onend = () => {
      if (token === speakToken) opts?.onEnd?.()
    }
    utter.onerror = () => {
      if (token === speakToken) opts?.onEnd?.()
    }
    try {
      window.speechSynthesis.speak(utter)
    } catch {
      opts?.onEnd?.()
    }
  })
}
