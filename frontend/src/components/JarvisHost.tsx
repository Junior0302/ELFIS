import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { findNavItem, spokenPageScript } from '../navConfig'
import {
  cancelSpeech,
  getJarvisAnnounceEnabled,
  isJarvisUnlocked,
  markWelcomeDoneThisSession,
  setJarvisAnnounceEnabled,
  setJarvisUnlocked,
  speakFrench,
  speechSupported,
  warmSpeechVoices,
  welcomeDoneThisSession,
} from '../voice/speech'

function greetingHour() {
  const h = new Date().getHours()
  if (h < 12) return 'Bonjour'
  if (h < 18) return 'Bon après-midi'
  return 'Bonsoir'
}

export default function JarvisHost() {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const item = findNavItem(pathname)
  const [showWelcome, setShowWelcome] = useState(false)
  const [announce, setAnnounce] = useState(getJarvisAnnounceEnabled)
  const [unlocked, setUnlocked] = useState(isJarvisUnlocked)
  const [speaking, setSpeaking] = useState(false)
  const [supported] = useState(speechSupported)
  const firstName = user?.first_name?.trim() || 'là'

  useEffect(() => {
    warmSpeechVoices()
    if (typeof window === 'undefined') return
    window.speechSynthesis?.addEventListener('voiceschanged', warmSpeechVoices)
    if (!welcomeDoneThisSession()) setShowWelcome(true)
    return () => {
      window.speechSynthesis?.removeEventListener('voiceschanged', warmSpeechVoices)
    }
  }, [])

  useEffect(() => {
    if (!announce || !unlocked || !item || showWelcome) return
    if (!supported) return
    if (item.to === '/copilote') return

    const script = item.spokenIntro
    const timer = window.setTimeout(() => {
      speakFrench(script, {
        onStart: () => setSpeaking(true),
        onEnd: () => setSpeaking(false),
      })
    }, 480)
    return () => {
      window.clearTimeout(timer)
      cancelSpeech()
      setSpeaking(false)
    }
  }, [announce, unlocked, pathname, showWelcome, supported, item])

  const activate = (withAnnounce: boolean) => {
    setJarvisUnlocked()
    setUnlocked(true)
    setJarvisAnnounceEnabled(withAnnounce)
    setAnnounce(withAnnounce)
    markWelcomeDoneThisSession()
    setShowWelcome(false)
    const welcome =
      `${greetingHour()} ${firstName}. Je suis ComptaPilot, votre assistant. ` +
      `Je vais vous guider sur chaque écran. ` +
      (withAnnounce
        ? 'Les explications vocales sont activées. Vous pouvez les couper à tout moment.'
        : 'Les explications vocales sont en pause. Réactivez-les quand vous voulez.')
    speakFrench(welcome, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    })
  }

  const dismiss = () => {
    markWelcomeDoneThisSession()
    setShowWelcome(false)
  }

  const toggleAnnounce = () => {
    const next = !announce
    setAnnounce(next)
    setJarvisAnnounceEnabled(next)
    if (!next) {
      cancelSpeech()
      setSpeaking(false)
    } else if (item) {
      setJarvisUnlocked()
      setUnlocked(true)
      speakFrench(item.spokenIntro, {
        onStart: () => setSpeaking(true),
        onEnd: () => setSpeaking(false),
      })
    }
  }

  const replayGuide = () => {
    if (!item) return
    setJarvisUnlocked()
    setUnlocked(true)
    speakFrench(spokenPageScript(item), {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    })
  }

  return (
    <>
      {showWelcome && (
        <div className="jarvis-welcome" role="dialog" aria-modal="true" aria-labelledby="jarvis-welcome-title">
          <div className="jarvis-welcome-card">
            <div className="jarvis-welcome-orb" aria-hidden>
              <span />
            </div>
            <p className="jarvis-welcome-kicker">Assistant ComptaPilot</p>
            <h2 id="jarvis-welcome-title">
              {greetingHour()} {firstName}
            </h2>
            <p>
              Je suis votre copilote. Style Siri / Jarvis : à chaque onglet, je vous explique à quoi
              il sert. Vous pouvez aussi me parler dans Copilote IA.
            </p>
            <div className="jarvis-welcome-actions">
              <button type="button" className="btn" onClick={() => activate(true)} disabled={!supported}>
                Activer l’accueil vocal
              </button>
              <button type="button" className="btn secondary" onClick={() => activate(false)}>
                Entrer sans voix
              </button>
              <button type="button" className="linkish" onClick={dismiss}>
                Plus tard
              </button>
            </div>
            {!supported && (
              <p className="muted jarvis-welcome-hint">
                Synthèse vocale indisponible ici — les guides texte restent affichés.
              </p>
            )}
          </div>
        </div>
      )}

      <div className={`jarvis-fab ${speaking ? 'is-speaking' : ''}`}>
        <button
          type="button"
          className={`jarvis-fab-btn ${announce ? 'is-on' : ''}`}
          onClick={toggleAnnounce}
          title={announce ? 'Couper les explications vocales' : 'Activer les explications vocales'}
          aria-pressed={announce}
        >
          {announce ? 'Voix on' : 'Voix off'}
        </button>
        {item && (
          <button type="button" className="jarvis-fab-btn secondary" onClick={replayGuide}>
            Expliquer
          </button>
        )}
        <Link to="/copilote?voice=1" className="jarvis-fab-btn accent">
          Parler
        </Link>
      </div>
    </>
  )
}
