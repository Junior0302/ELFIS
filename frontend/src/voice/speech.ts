/** Synthèse vocale FR partagée (accueil Jarvis + onglets + copilote). */

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

export function warmSpeechVoices(): void {
  if (!speechSupported()) return
  void pickFrenchVoice()
  window.speechSynthesis.getVoices()
}

export function cancelSpeech(): void {
  if (!speechSupported()) return
  window.speechSynthesis.cancel()
}

export function speakFrench(
  text: string,
  opts?: {
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
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text.trim())
  utter.lang = 'fr-FR'
  utter.rate = opts?.rate ?? 1.02
  utter.pitch = opts?.pitch ?? 0.98
  const voice = pickFrenchVoice()
  if (voice) utter.voice = voice
  utter.onstart = () => opts?.onStart?.()
  utter.onend = () => opts?.onEnd?.()
  utter.onerror = () => opts?.onEnd?.()
  window.speechSynthesis.speak(utter)
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
