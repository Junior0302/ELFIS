/** Synthèse vocale FR partagée (accueil Jarvis + onglets + copilote). */

let speakToken = 0
let voicesReady: Promise<void> | null = null

export function speechSupported(): boolean {
  return typeof window !== 'undefined' && Boolean(window.speechSynthesis)
}

function pickFrenchVoice(): SpeechSynthesisVoice | null {
  if (!speechSupported()) return null
  const voices = window.speechSynthesis.getVoices()
  const fr = voices.filter((v) => v.lang.toLowerCase().startsWith('fr'))
  return (
    fr.find((v) => /google|natural|enhanced|premium/i.test(v.name)) ||
    fr.find((v) => /france|fr-fr/i.test(v.lang)) ||
    fr[0] ||
    null
  )
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
    utter.rate = opts?.rate ?? 1.02
    utter.pitch = opts?.pitch ?? 0.98
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

export const JARVIS_ANNOUNCE_KEY = 'cp_jarvis_announce'
export const JARVIS_UNLOCKED_KEY = 'cp_jarvis_unlocked'
export const JARVIS_WELCOME_SESSION_KEY = 'cp_jarvis_welcome_done'

export function getJarvisAnnounceEnabled(): boolean {
  try {
    return localStorage.getItem(JARVIS_ANNOUNCE_KEY) !== '0'
  } catch {
    return true
  }
}

export function setJarvisAnnounceEnabled(on: boolean): void {
  try {
    localStorage.setItem(JARVIS_ANNOUNCE_KEY, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}

export function isJarvisUnlocked(): boolean {
  try {
    return localStorage.getItem(JARVIS_UNLOCKED_KEY) === '1'
  } catch {
    return false
  }
}

export function setJarvisUnlocked(): void {
  try {
    localStorage.setItem(JARVIS_UNLOCKED_KEY, '1')
  } catch {
    /* ignore */
  }
}

export function welcomeDoneThisSession(): boolean {
  try {
    return sessionStorage.getItem(JARVIS_WELCOME_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

export function markWelcomeDoneThisSession(): void {
  try {
    sessionStorage.setItem(JARVIS_WELCOME_SESSION_KEY, '1')
  } catch {
    /* ignore */
  }
}
